import pytest

from ceibo_core.security.ollama_guard import validate_ollama_base_url, UnsafeOllamaHostError


def test_accepts_localhost():
    validate_ollama_base_url("http://localhost:11434")


def test_accepts_127():
    validate_ollama_base_url("http://127.0.0.1:11434")


def test_blocks_0_0_0_0():
    with pytest.raises(UnsafeOllamaHostError):
        validate_ollama_base_url("http://0.0.0.0:11434")


def test_blocks_private_ip():
    with pytest.raises(UnsafeOllamaHostError):
        validate_ollama_base_url("http://192.168.1.5:11434")
