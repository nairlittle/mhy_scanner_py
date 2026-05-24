"""账号管理路由"""

from fastapi import APIRouter, HTTPException

from .. import database
from ..schemas import AccountCreate, AccountUpdate, AccountResponse

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _sanitize(account: dict) -> dict:
    """移除敏感字段（stoken不返回给前端）"""
    return {k: v for k, v in account.items() if k != "stoken"}


@router.get("")
async def list_accounts():
    """获取所有账号（不含stoken）"""
    accounts = database.get_all_accounts()
    return {"retcode": 0, "data": [_sanitize(a) for a in accounts]}


@router.get("/{account_id}")
async def get_account(account_id: int):
    """获取单个账号（不含stoken）"""
    account = database.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return {"retcode": 0, "data": _sanitize(account)}


@router.post("")
async def create_account(req: AccountCreate):
    """添加账号"""
    account = database.add_account(
        name=req.name,
        stoken=req.stoken,
        uid=req.uid,
        mid=req.mid or "",
        server=req.server.value if hasattr(req.server, 'value') else str(req.server),
        note=req.note or ""
    )
    return {"retcode": 0, "data": account}


@router.put("/{account_id}")
async def update_account(account_id: int, req: AccountUpdate):
    """更新账号"""
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    if "server" in update_data and hasattr(update_data["server"], 'value'):
        update_data["server"] = update_data["server"].value
    
    account = database.update_account(account_id, **update_data)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    return {"retcode": 0, "data": account}


@router.delete("/{account_id}")
async def delete_account(account_id: int):
    """删除账号"""
    if not database.delete_account(account_id):
        raise HTTPException(status_code=404, detail="账号不存在")
    return {"retcode": 0, "message": "删除成功"}
