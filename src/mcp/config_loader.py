"""
Utility helpers to load external MCP server definitions from JSON/YAML files.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from .base import MCPServerConfig

logger = logging.getLogger(__name__)

PLACEHOLDER_PATTERN = re.compile(r"^\$\{([A-Z0-9_]+)\}$")
DEFAULT_CONFIG_PATH = Path("config/mcp_servers.json")


def _resolve_placeholder(value: str) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Resolve ${ENV_VAR} style placeholders.

    Returns:
        (success, resolved_value, missing_var_name)
    """
    if not isinstance(value, str):
        return True, value, None

    match = PLACEHOLDER_PATTERN.match(value.strip())
    if not match:
        return True, value, None

    env_name = match.group(1)
    resolved = os.environ.get(env_name)
    if not resolved:
        return False, None, env_name
    return True, resolved, None


def _normalize_args(raw_args: List[str]) -> Optional[List[str]]:
    args: List[str] = []
    for item in raw_args or []:
        ok, resolved, missing = _resolve_placeholder(item)
        if not ok:
            logger.warning("MCP 服务器参数缺少环境变量 %s，已跳过", missing)
            return None
        args.append(resolved or "")
    return args


def _normalize_env(raw_env: Dict[str, str]) -> Optional[Dict[str, str]]:
    env: Dict[str, str] = {}
    for key, value in (raw_env or {}).items():
        ok, resolved, missing = _resolve_placeholder(value)
        if not ok:
            logger.warning("MCP 服务器环境变量 %s 未设置，已跳过 (%s)", missing, key)
            return None
        if resolved is None:
            continue
        env[key] = resolved
    return env


def load_external_mcp_configs(config_path: Optional[Path] = None) -> List[MCPServerConfig]:
    """
    Load MCP server definitions from config/mcp_servers.json (or custom path).

    Config format (JSON):
    {
      "servers": [
        {
          "name": "context7",
          "type": "stdio",
          "command": "npx",
          "args": ["-y", "@upstash/context7-mcp"],
          "env": {"CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"},
          "cwd": null,
          "enabled": true
        }
      ]
    }
    """

    path = config_path or Path(os.environ.get("NEXUS_MCP_CONFIG", DEFAULT_CONFIG_PATH))
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("无法解析 MCP 配置文件 %s: %s", path, exc)
        return []

    server_entries = data.get("servers", [])
    configs: List[MCPServerConfig] = []

    for entry in server_entries:
        name = entry.get("name")
        server_type = entry.get("type", "stdio")
        if not name:
            logger.warning("检测到缺少名称的 MCP 服务器配置，已跳过")
            continue

        command_value = entry.get("command")
        command = None
        if command_value is not None:
            ok, resolved, missing = _resolve_placeholder(command_value)
            if not ok:
                logger.warning("MCP 服务器 %s 缺少命令环境变量 %s，已跳过", name, missing)
                continue
            command = resolved

        args = _normalize_args(entry.get("args", []))
        if args is None:
            logger.warning("MCP 服务器 %s 参数不完整，已跳过", name)
            continue

        env = _normalize_env(entry.get("env", {}))
        if env is None:
            logger.warning("MCP 服务器 %s 环境变量缺失，已跳过", name)
            continue

        cwd = entry.get("cwd")
        if cwd:
            ok, resolved, missing = _resolve_placeholder(cwd)
            if not ok:
                logger.warning("MCP 服务器 %s 缺少工作目录环境变量 %s，已跳过", name, missing)
                continue
            cwd = resolved

        configs.append(
            MCPServerConfig(
                name=name,
                type=server_type,
                command=command,
                args=args,
                env=env or {},
                cwd=cwd,
                enabled=entry.get("enabled", True),
                url=entry.get("url"),
                api_key=entry.get("api_key"),
            )
        )

    if configs:
        logger.info("已加载 %d 个外部 MCP 服务器配置", len(configs))
    return configs

