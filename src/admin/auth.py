"""
Admin 认证模块

提供简单的密码认证机制
"""

import os
import hashlib
import hmac
from typing import Optional

# 环境变量名
ADMIN_PASSWORD_ENV = "NEXUS_ADMIN_PASSWORD"
DEFAULT_PASSWORD = "nexus_admin_2024"  # 默认密码，建议用户修改


def get_admin_password() -> str:
    """获取 Admin 密码"""
    return os.environ.get(ADMIN_PASSWORD_ENV, DEFAULT_PASSWORD)


def get_admin_password_hash() -> str:
    """获取 Admin 密码的哈希值（用于前端存储）"""
    password = get_admin_password()
    return hashlib.sha256(password.encode()).hexdigest()


def verify_admin_password(password: str) -> bool:
    """验证 Admin 密码"""
    correct_password = get_admin_password()
    # 使用 hmac.compare_digest 防止时序攻击
    return hmac.compare_digest(password, correct_password)


def verify_admin_token(token: str) -> bool:
    """验证 Admin Token（密码的 SHA256 哈希）"""
    correct_hash = get_admin_password_hash()
    return hmac.compare_digest(token, correct_hash)


def create_admin_token(password: str) -> Optional[str]:
    """创建 Admin Token（如果密码正确）"""
    if verify_admin_password(password):
        return get_admin_password_hash()
    return None

