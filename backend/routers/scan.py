"""扫码路由 - 游戏扫码登录"""

from fastapi import APIRouter

from .. import database
from ..schemas import QRCodeScanRequest
from ..services import mhy_api

router = APIRouter(prefix="/api/scan", tags=["scan"])


@router.post("/game")
async def scan_game_qr(req: QRCodeScanRequest):
    """使用已保存的账号扫码登录游戏
    
    当从屏幕或直播流中识别到游戏登录二维码时，调用此接口进行扫码确认。
    """
    account = database.get_account(req.account_id)
    if not account:
        return {"retcode": -1, "message": "账号不存在"}
    
    result = await mhy_api.qrcode_scan(
        game=req.game.value,
        ticket=req.ticket,
        stoken=account["stoken"],
        uid=account["uid"],
        mid=account.get("mid", ""),
        server=account.get("server", "官服")
    )
    
    if result["retcode"] == 0:
        return {"retcode": 0, "message": f"账号[{account['name']}]扫码成功"}
    return {"retcode": -1, "message": result.get("message", "扫码确认失败")}
