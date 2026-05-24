"""扫码路由 - 游戏扫码登录"""

from fastapi import APIRouter

from .. import database
from ..schemas import QRCodeScanRequest, LiveScanRequest
from ..services import mhy_api

router = APIRouter(prefix="/api/scan", tags=["scan"])


@router.post("/game")
async def scan_game_qr(req: QRCodeScanRequest):
    """使用已保存的账号扫码登录游戏
    
    当从屏幕或直播流中识别到游戏登录二维码时，调用此接口进行扫码确认。
    """
    account = database.get_account(req.account_id)
    if not account:
        print(f"[SCAN] 账号不存在 id={req.account_id}")
        return {"retcode": -1, "message": "账号不存在"}
    
    print(f"[SCAN] game={req.game} ticket={req.ticket[:50]}... account={account['name']}({account['uid']}) server={account.get('server')}")
    
    result = await mhy_api.qrcode_scan(
        game=req.game.value if hasattr(req.game, 'value') else req.game,
        ticket=req.ticket,
        stoken=account["stoken"],
        uid=account["uid"],
        mid=account.get("mid", ""),
        server=account.get("server", "官服")
    )
    
    print(f"[SCAN] 结果: retcode={result.get('retcode')} msg={result.get('message', '')[:50]}")
    
    if result["retcode"] == 0:
        return {"retcode": 0, "message": f"账号[{account['name']}]扫码成功"}
    return {"retcode": -1, "message": result.get("message", "扫码确认失败")}
