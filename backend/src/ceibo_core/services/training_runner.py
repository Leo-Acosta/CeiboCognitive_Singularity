import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ceibo_core.models.schemas import (
    QloraTrainingRequest,
    TrainingDryRunReport,
    TrainingPromotionGate,
    TrainingRunnerDependency,
    TrainingRunnerReport,
    TrainingRunStatus,
)


class TrainingRunnerService:
    def project_root(self) -> Path:
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "docker-compose.yml").exists():
                return parent
            if (parent / "pyproject.toml").exists() and (parent / "training").exists():
                return parent
        return current.parents[4]

    def runs_dir(self) -> Path:
        return self.project_root() / "training" / "runs"

    def runner_script(self) -> Path:
        return self.project_root() / "training" / "scripts" / "run_qlora.py"

    def runner_python(self) -> str:
        windows_venv_python = self.project_root() / ".venv-qlora" / "Scripts" / "python.exe"
        unix_venv_python = self.project_root() / ".venv-qlora" / "bin" / "python"
        if windows_venv_python.exists():
            return str(windows_venv_python)
        if unix_venv_python.exists():
            return str(unix_venv_python)
        return sys.executable

    def preflight(self, request: QloraTrainingRequest) -> TrainingRunnerReport:
        run_id = self._new_run_id()
        command = self._build_command(request, run_id=run_id, preflight_only=True)
        result = subprocess.run(
            command,
            cwd=self.project_root(),
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        report = self.get_run(run_id)
        if result.returncode not in (0, 2) and report.status != TrainingRunStatus.FAILED:
            return report.model_copy(
                update={
                    "status": TrainingRunStatus.FAILED,
                    "warnings": [*report.warnings, result.stderr.strip() or result.stdout.strip()],
                    "completed_at": datetime.now(UTC),
                }
            )
        return report

    def dry_run(
        self,
        request: QloraTrainingRequest,
        gate: TrainingPromotionGate,
    ) -> TrainingDryRunReport:
        run_id = self._new_run_id(prefix="dryrun")
        command = self._build_command(request, run_id=run_id, preflight_only=True)
        config_path = self._resolve_project_path(request.config_path)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        dataset_path = self._resolve_project_path(request.dataset_path or config["dataset"])
        output_dir = self._resolve_project_path(request.output_dir or config["output_dir"])
        dataset_examples = self._count_jsonl(dataset_path)
        warnings = list(gate.warnings)
        blockers = list(gate.blockers)

        if dataset_examples == 0:
            blockers.append("El dataset resuelto no contiene ejemplos.")
        if request.local_files_only is not True:
            warnings.append("Dry run recomienda local_files_only=true para evitar descargas.")
        if (request.max_steps or 1) > 10:
            warnings.append("Dry run recomienda max_steps <= 10 hasta tener evidencia estable.")

        allowed = gate.allowed and not blockers
        status = TrainingRunStatus.READY if allowed else TrainingRunStatus.BLOCKED
        if allowed:
            summary = "Dry run listo: se puede ejecutar preflight QLoRA sin entrenamiento real."
            next_actions = [
                "Ejecutar /training/qlora/preflight con la misma configuracion.",
                "Revisar manifest y logs antes de cualquier entrenamiento real.",
            ]
        else:
            summary = "Dry run bloqueado: falta evidencia suficiente para preflight seguro."
            next_actions = [
                "Resolver blockers del Promotion Gate.",
                "No ejecutar preflight ni entrenamiento hasta que el dry run quede listo.",
            ]

        return TrainingDryRunReport(
            run_id=run_id,
            allowed=allowed,
            status=status,
            summary=summary,
            config_path=str(config_path),
            dataset_path=str(dataset_path),
            output_dir=str(output_dir),
            base_model=request.base_model or config["base_model"],
            command=command,
            dataset_examples=dataset_examples,
            estimated_steps=request.max_steps or 1,
            gate=gate,
            blockers=list(dict.fromkeys(blockers)),
            warnings=list(dict.fromkeys(warnings)),
            next_actions=next_actions,
        )

    def start(self, request: QloraTrainingRequest) -> TrainingRunnerReport:
        run_id = self._new_run_id()
        run_dir = self.runs_dir() / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        log_path = run_dir / "process.log"
        command = self._build_command(request, run_id=run_id, preflight_only=False)
        with log_path.open("w", encoding="utf-8") as log_file:
            subprocess.Popen(
                command,
                cwd=self.project_root(),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )
        report = self._initial_report(request, run_id, command, log_path)
        self._write_report(report)
        return report

    def list_runs(self, limit: int = 20) -> list[TrainingRunnerReport]:
        runs = []
        for manifest_path in sorted(
            self.runs_dir().glob("*/manifest.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )[:limit]:
            runs.append(self._read_report(manifest_path))
        return runs

    def get_run(self, run_id: str) -> TrainingRunnerReport:
        manifest_path = self.runs_dir() / run_id / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Training run not found: {run_id}")
        return self._read_report(manifest_path)

    def _build_command(
        self,
        request: QloraTrainingRequest,
        *,
        run_id: str,
        preflight_only: bool,
    ) -> list[str]:
        command = [
            self.runner_python(),
            str(self.runner_script()),
            "--config",
            request.config_path,
            "--run-id",
            run_id,
        ]
        if request.dataset_path:
            command.extend(["--dataset", request.dataset_path])
        if request.output_dir:
            command.extend(["--output-dir", request.output_dir])
        if request.base_model:
            command.extend(["--base-model", request.base_model])
        if request.max_steps is not None:
            command.extend(["--max-steps", str(request.max_steps)])
        if request.local_files_only is True:
            command.append("--local-files-only")
        elif request.local_files_only is False:
            command.append("--allow-download")
        if preflight_only:
            command.append("--preflight-only")
        return command

    def _initial_report(
        self,
        request: QloraTrainingRequest,
        run_id: str,
        command: list[str],
        log_path: Path,
    ) -> TrainingRunnerReport:
        config_path = self._resolve_project_path(request.config_path)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        dataset_path = self._resolve_project_path(request.dataset_path or config["dataset"])
        output_dir = self._resolve_project_path(request.output_dir or config["output_dir"])
        return TrainingRunnerReport(
            run_id=run_id,
            status=TrainingRunStatus.RUNNING,
            config_path=str(config_path),
            dataset_path=str(dataset_path),
            output_dir=str(output_dir),
            base_model=request.base_model or config["base_model"],
            command=command,
            dataset_examples=self._count_jsonl(dataset_path),
            dependencies=[
                TrainingRunnerDependency(name="runner_process", available=True, required=True)
            ],
            log_path=str(log_path),
            manifest_path=str(self.runs_dir() / run_id / "manifest.json"),
        )

    def _read_report(self, manifest_path: Path) -> TrainingRunnerReport:
        return TrainingRunnerReport.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    def _write_report(self, report: TrainingRunnerReport) -> None:
        manifest_path = Path(report.manifest_path or "")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    def _new_run_id(self, prefix: str = "qlora") -> str:
        return f"{prefix}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"

    def _resolve_project_path(self, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.project_root() / path
        return path.resolve()

    def _count_jsonl(self, path: Path) -> int:
        if not path.exists():
            return 0
        return sum(1 for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip())


training_runner_service = TrainingRunnerService()
