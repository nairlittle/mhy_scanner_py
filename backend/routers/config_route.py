"""配置管理路由 - 持久化用户设置"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import get_config, update_config, load_config

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
async def get_user_config():
    """获取完整配置"""
    return JSONResponse(load_config())


@router.put("/{key}")
async def update_user_config(key: str, value: str = ""):
    """更新单个配置项

    支持类型自动转换:
    - "true"/"false" -> bool
    - 纯数字 -> int
    - 其他 -> str
    """
    if value.lower() == "true":
        val = True
    elif value.lower() == "false":
        val = False
    elif value.isdigit():
        val = int(value)
    else:
        val = value

    config = update_config(key, val)
    return JSONResponse(config)
