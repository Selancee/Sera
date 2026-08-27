import json
import socket
import importlib.util
from pathlib import Path

import pytest


def load_packaged_backend_module():
    path = Path(__file__).resolve().parents[1] / "packaging" / "backend" / "run_backend_packaged.py"
    spec = importlib.util.spec_from_file_location("sera_packaged_backend", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_find_available_port_skips_occupied_port() -> None:
    module = load_packaged_backend_module()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen(1)
        occupied = busy.getsockname()[1]

        selected = module.find_available_port(occupied, max_attempts=3)

    assert selected != occupied


def test_write_runtime_port_file(tmp_path) -> None:
    module = load_packaged_backend_module()
    path = module.write_runtime_port_file(8123, tmp_path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["port"] == 8123
    assert payload["base_url"] == "http://127.0.0.1:8123"


def test_desktop_mode_refuses_to_silently_change_plugin_port(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_packaged_backend_module()
    monkeypatch.setenv("SERA_DESKTOP_STRICT_PORT", "1")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen(1)
        occupied = busy.getsockname()[1]

        with pytest.raises(RuntimeError):
            module.resolve_backend_port(occupied)
