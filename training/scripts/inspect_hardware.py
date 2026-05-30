import json
import platform
import shutil
import subprocess


def inspect_nvidia() -> dict:
    if not shutil.which("nvidia-smi"):
        return {"has_cuda": False, "gpu_vram_gb": 0, "device": "cpu"}
    command = [
        "nvidia-smi",
        "--query-gpu=name,memory.total",
        "--format=csv,noheader,nounits",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return {"has_cuda": False, "gpu_vram_gb": 0, "device": "cpu"}
    name, memory_mb = result.stdout.splitlines()[0].split(",", maxsplit=1)
    return {
        "has_cuda": True,
        "gpu_vram_gb": round(int(memory_mb.strip()) / 1024),
        "device": name.strip(),
    }


def main() -> None:
    profile = {
        "system": platform.system(),
        "machine": platform.machine(),
        **inspect_nvidia(),
    }
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
