"""应用配置管理 - 持久化用户设置 (对齐原版 ConfigDate)"""

import json
import os
from threading import Lock

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "userinfo.json")

DEFAULT_CONFIG = {
    "auto_exit": False,
    "auto_login": False,
    "auto_start": False,
    "last_account": 0,
    "last_game": "hk4e",
    "last_live_platform": "bilibili",
    "last_live_room_id": "",
}

_lock = Lock()


def _ensure_config_dir():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)


def init_config():
    """初始化配置文件（如果不存在则创建默认配置）"""
    _ensure_config_dir()
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)


def load_config() -> dict:
    """读取配置文件"""
    _ensure_config_dir()
    if not os.path.exists(CONFIG_FILE):
        init_config()
        return dict(DEFAULT_CONFIG)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        merged = dict(DEFAULT_CONFIG)
        merged.update(config)
        return merged
    except (json.JSONDecodeError, IOError):
        return dict(DEFAULT_CONFIG)


def save_config(config: dict):
    """保存配置文件"""
    _ensure_config_dir()
    current = load_config()
    current.update(config)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=4, ensure_ascii=False)


def get_config() -> dict:
    """获取完整配置"""
    return load_config()


def update_config(key: str, value) -> dict:
    """更新单个配置项"""
    current = load_config()
    current[key] = value
    save_config(current)
    return current


def set_last_account(account_id: int):
    update_config("last_account", account_id)


def set_last_game(game: str):
    update_config("last_game", game)


def set_last_live(platform: str, room_id: str):
    current = load_config()
    current["last_live_platform"] = platform
    current["last_live_room_id"] = room_id
    save_config(current)
