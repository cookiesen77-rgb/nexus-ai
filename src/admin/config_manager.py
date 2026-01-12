"""
统一配置管理器

管理工具、MCP、Skills 的配置
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
TOOLS_CONFIG_PATH = CONFIG_DIR / "tools.json"
MCP_CONFIG_PATH = CONFIG_DIR / "mcp_servers.json"
SKILLS_CONFIG_PATH = CONFIG_DIR / "skills.json"


class ConfigManager:
    """统一配置管理器"""

    _instance: Optional["ConfigManager"] = None

    def __init__(self):
        self._tools_config: Dict[str, Any] = {}
        self._mcp_config: Dict[str, Any] = {}
        self._skills_config: Dict[str, Any] = {}
        self._load_all_configs()

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = ConfigManager()
        return cls._instance

    def _load_all_configs(self):
        """加载所有配置文件"""
        self._load_tools_config()
        self._load_mcp_config()
        self._load_skills_config()

    def _load_tools_config(self):
        """加载工具配置"""
        if TOOLS_CONFIG_PATH.exists():
            try:
                with open(TOOLS_CONFIG_PATH, "r", encoding="utf-8") as f:
                    self._tools_config = json.load(f)
                logger.info(f"已加载工具配置: {len(self._tools_config.get('tools', {}))} 个工具")
            except Exception as e:
                logger.error(f"加载工具配置失败: {e}")
                self._tools_config = {"version": "1.0", "tools": {}}
        else:
            self._tools_config = {"version": "1.0", "tools": {}}

    def _load_mcp_config(self):
        """加载 MCP 配置"""
        if MCP_CONFIG_PATH.exists():
            try:
                with open(MCP_CONFIG_PATH, "r", encoding="utf-8") as f:
                    self._mcp_config = json.load(f)
                logger.info(f"已加载 MCP 配置: {len(self._mcp_config.get('servers', []))} 个服务器")
            except Exception as e:
                logger.error(f"加载 MCP 配置失败: {e}")
                self._mcp_config = {"servers": []}
        else:
            self._mcp_config = {"servers": []}

    def _load_skills_config(self):
        """加载 Skills 配置"""
        if SKILLS_CONFIG_PATH.exists():
            try:
                with open(SKILLS_CONFIG_PATH, "r", encoding="utf-8") as f:
                    self._skills_config = json.load(f)
                logger.info(f"已加载 Skills 配置: {len(self._skills_config.get('skills', {}))} 个技能")
            except Exception as e:
                logger.error(f"加载 Skills 配置失败: {e}")
                self._skills_config = {"version": "1.0", "skills": {}}
        else:
            self._skills_config = {"version": "1.0", "skills": {}}

    # ==================== 工具管理 ====================

    def get_tools_config(self) -> Dict[str, Any]:
        """获取所有工具配置"""
        return self._tools_config

    def get_enabled_tools(self) -> List[str]:
        """获取所有启用的工具名称"""
        tools = self._tools_config.get("tools", {})
        return [name for name, config in tools.items() if config.get("enabled", True)]

    def is_tool_enabled(self, name: str) -> bool:
        """检查工具是否启用"""
        tools = self._tools_config.get("tools", {})
        if name not in tools:
            return True  # 默认启用
        return tools[name].get("enabled", True)

    def get_tool_config(self, name: str) -> Optional[Dict[str, Any]]:
        """获取单个工具配置"""
        return self._tools_config.get("tools", {}).get(name)

    def update_tool(self, name: str, updates: Dict[str, Any]) -> bool:
        """更新工具配置"""
        if "tools" not in self._tools_config:
            self._tools_config["tools"] = {}

        if name not in self._tools_config["tools"]:
            self._tools_config["tools"][name] = {}

        self._tools_config["tools"][name].update(updates)
        return self._save_tools_config()

    def set_tool_enabled(self, name: str, enabled: bool) -> bool:
        """设置工具启用状态"""
        return self.update_tool(name, {"enabled": enabled})

    def _save_tools_config(self) -> bool:
        """保存工具配置"""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(TOOLS_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._tools_config, f, ensure_ascii=False, indent=2)
            logger.info("工具配置已保存")
            return True
        except Exception as e:
            logger.error(f"保存工具配置失败: {e}")
            return False

    # ==================== MCP 管理 ====================

    def get_mcp_config(self) -> Dict[str, Any]:
        """获取所有 MCP 配置"""
        return self._mcp_config

    def get_mcp_servers(self) -> List[Dict[str, Any]]:
        """获取所有 MCP 服务器配置"""
        return self._mcp_config.get("servers", [])

    def get_enabled_mcp_servers(self) -> List[Dict[str, Any]]:
        """获取所有启用的 MCP 服务器"""
        servers = self._mcp_config.get("servers", [])
        return [s for s in servers if s.get("enabled", True)]

    def get_mcp_server(self, name: str) -> Optional[Dict[str, Any]]:
        """获取单个 MCP 服务器配置"""
        servers = self._mcp_config.get("servers", [])
        for server in servers:
            if server.get("name") == name:
                return server
        return None

    def update_mcp_server(self, name: str, updates: Dict[str, Any]) -> bool:
        """更新 MCP 服务器配置"""
        servers = self._mcp_config.get("servers", [])
        for i, server in enumerate(servers):
            if server.get("name") == name:
                servers[i].update(updates)
                return self._save_mcp_config()
        return False

    def set_mcp_enabled(self, name: str, enabled: bool) -> bool:
        """设置 MCP 服务器启用状态"""
        return self.update_mcp_server(name, {"enabled": enabled})

    def add_mcp_server(self, config: Dict[str, Any]) -> bool:
        """添加新 MCP 服务器"""
        if "servers" not in self._mcp_config:
            self._mcp_config["servers"] = []

        # 检查是否已存在
        name = config.get("name")
        if name and self.get_mcp_server(name):
            logger.warning(f"MCP 服务器 '{name}' 已存在")
            return False

        self._mcp_config["servers"].append(config)
        return self._save_mcp_config()

    def delete_mcp_server(self, name: str) -> bool:
        """删除 MCP 服务器"""
        servers = self._mcp_config.get("servers", [])
        original_len = len(servers)
        self._mcp_config["servers"] = [s for s in servers if s.get("name") != name]

        if len(self._mcp_config["servers"]) < original_len:
            return self._save_mcp_config()
        return False

    def _save_mcp_config(self) -> bool:
        """保存 MCP 配置"""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(MCP_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._mcp_config, f, ensure_ascii=False, indent=2)
            logger.info("MCP 配置已保存")
            return True
        except Exception as e:
            logger.error(f"保存 MCP 配置失败: {e}")
            return False

    # ==================== Skills 管理 ====================

    def get_skills_config(self) -> Dict[str, Any]:
        """获取所有 Skills 配置"""
        return self._skills_config

    def get_enabled_skills(self) -> List[str]:
        """获取所有启用的 Skills 名称"""
        skills = self._skills_config.get("skills", {})
        return [name for name, config in skills.items() if config.get("enabled", True)]

    def is_skill_enabled(self, name: str) -> bool:
        """检查 Skill 是否启用"""
        skills = self._skills_config.get("skills", {})
        if name not in skills:
            return True
        return skills[name].get("enabled", True)

    def update_skill(self, name: str, updates: Dict[str, Any]) -> bool:
        """更新 Skill 配置"""
        if "skills" not in self._skills_config:
            self._skills_config["skills"] = {}

        if name not in self._skills_config["skills"]:
            self._skills_config["skills"][name] = {}

        self._skills_config["skills"][name].update(updates)
        return self._save_skills_config()

    def add_skill(self, name: str, config: Dict[str, Any]) -> bool:
        """添加新 Skill"""
        if "skills" not in self._skills_config:
            self._skills_config["skills"] = {}

        if name in self._skills_config["skills"]:
            logger.warning(f"Skill '{name}' 已存在")
            return False

        self._skills_config["skills"][name] = config
        return self._save_skills_config()

    def delete_skill(self, name: str) -> bool:
        """删除 Skill"""
        skills = self._skills_config.get("skills", {})
        if name in skills:
            del self._skills_config["skills"][name]
            return self._save_skills_config()
        return False

    def _save_skills_config(self) -> bool:
        """保存 Skills 配置"""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(SKILLS_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._skills_config, f, ensure_ascii=False, indent=2)
            logger.info("Skills 配置已保存")
            return True
        except Exception as e:
            logger.error(f"保存 Skills 配置失败: {e}")
            return False

    # ==================== 热重载 ====================

    def reload_all(self):
        """重新加载所有配置"""
        self._load_all_configs()
        logger.info("所有配置已重新加载")

    def reload_tools(self):
        """重新加载工具配置"""
        self._load_tools_config()

    def reload_mcp(self):
        """重新加载 MCP 配置"""
        self._load_mcp_config()

    def reload_skills(self):
        """重新加载 Skills 配置"""
        self._load_skills_config()


# 全局单例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

