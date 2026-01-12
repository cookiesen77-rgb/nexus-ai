import json
import os
from pathlib import Path

from src.mcp.config_loader import load_external_mcp_configs


def write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "mcp.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_config_with_placeholders(monkeypatch, tmp_path):
    cfg = {
        "servers": [
            {
                "name": "test",
                "type": "stdio",
                "command": "${TEST_CMD}",
                "args": ["foo", "${TEST_ARG}"],
                "env": {"TOKEN": "${TEST_TOKEN}"},
                "cwd": "${TEST_CWD}",
                "enabled": True,
            }
        ]
    }
    path = write_config(tmp_path, cfg)

    monkeypatch.setenv("NEXUS_MCP_CONFIG", str(path))
    monkeypatch.setenv("TEST_CMD", "echo")
    monkeypatch.setenv("TEST_ARG", "bar")
    monkeypatch.setenv("TEST_TOKEN", "secret")
    monkeypatch.setenv("TEST_CWD", "/tmp")

    configs = load_external_mcp_configs()
    assert len(configs) == 1
    config = configs[0]
    assert config.command == "echo"
    assert config.args == ["foo", "bar"]
    assert config.env["TOKEN"] == "secret"
    assert config.cwd == "/tmp"


def test_missing_env_skip(monkeypatch, tmp_path):
    cfg = {
        "servers": [
            {
                "name": "test",
                "type": "stdio",
                "command": "${UNSET_CMD}",
                "args": [],
                "env": {},
            }
        ]
    }
    path = write_config(tmp_path, cfg)
    monkeypatch.setenv("NEXUS_MCP_CONFIG", str(path))
    monkeypatch.delenv("UNSET_CMD", raising=False)

    configs = load_external_mcp_configs()
    assert configs == []

