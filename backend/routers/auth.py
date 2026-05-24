"""登录/认证路由"""

import re
from fastapi import APIRouter
from pydantic import BaseModel

from .. import database
from ..schemas import (
    SMSSendRequest, SMSLoginRequest, CookieLoginRequest,
    CaptchaResponse, LoginQRCodeResponse
)
from ..services import mhy_api, bh3_bili_api

router = APIRouter(prefix="/api/auth", tags=["auth"])


class BH3LoginRequest(BaseModel):
    """崩坏3B服登录请求"""
    account: str
    password: str
    gt_user_id: str = ""
    challenge: str = ""
    gee_validate: str = ""
    seccode: str = ""


@router.get("/qrcode", response_model=LoginQRCodeResponse)
async def get_login_qrcode():
    """获取米游社登录二维码"""
    url, ticket = await mhy_api.get_login_qrcode_url()
    return LoginQRCodeResponse(url=url, ticket=ticket)


@router.get("/qrcode/state/{ticket}")
async def check_qrcode_state(ticket: str):
    """查询二维码扫码状态"""
    result = await mhy_api.check_qrcode_state(ticket)
    return result


@router.post("/qrcode/login")
async def qrcode_login_complete(ticket: str, uid: str, game_token: str):
    """扫码登录完成 - 获取并保存SToken"""
    result = await mhy_api.get_stoken_by_game_token(uid, game_token)
    if result["retcode"] == 0:
        name = await mhy_api.get_username_by_uid(uid)
        account = database.add_account(
            name=name,
            stoken=result["stoken"],
            uid=uid,
            mid=result["mid"],
            server="官服"
        )
    return {"retcode": 0, "data": account}


# ============ 崩坏3 Bilibili服登录 ============

@router.get("/bh3_bili/captcha")
async def get_bh3_bili_captcha():
    """获取崩坏3B服登录的极验验证码参数"""
    try:
        result = await bh3_bili_api.start_captcha()
        return {"retcode": 0, "data": result}
    except Exception as e:
        return {"retcode": -1, "message": str(e)}


@router.post("/bh3_bili/login")
async def bh3_bili_login(req: BH3LoginRequest):
    """崩坏3B服账号登录"""
    try:
        result = await bh3_bili_api.login_by_password(
            account=req.account,
            password=req.password,
            gt_user_id=req.gt_user_id,
            challenge=req.challenge,
            validate=req.gee_validate,
            seccode=req.seccode,
        )

        if result["code"] == 0:
            # 保存BH3 B服账号 (access_key存入stoken字段)
            account = database.add_account(
                name=result["uname"],
                stoken=result["access_key"],
                uid=result["uid"],
                mid="",
                server="崩坏3B服",
                note=req.account
            )
            return {"retcode": 0, "data": account, "message": "登录成功"}

        return {"retcode": -1, "message": result.get("message", "登录失败")}
    except Exception as e:
        return {"retcode": -1, "message": str(e)}
    return {"retcode": -1, "message": result.get("message", "获取SToken失败")}


@router.post("/sms/send", response_model=CaptchaResponse)
async def send_sms_code(req: SMSSendRequest):
    """发送短信验证码
    
    首次请求不带aigis参数，如果返回mmt_type=5（需要极验），
    则需完成极验验证后带上aigis参数再次请求。
    """
    if not re.match(r"^1[3-9]\d{9}$", req.mobile):
        return CaptchaResponse(retcode=-3008, message="手机号格式错误")
    
    result = await mhy_api.create_login_captcha(req.mobile, req.aigis)
    return CaptchaResponse(
        retcode=result.get("retcode", -1),
        message=result.get("message", ""),
        action_type=result.get("data", {}).get("action_type", ""),
        mmt_type=result.get("data", {}).get("mmt_type", 0),
        gt=result.get("data", {}).get("gt", ""),
        challenge=result.get("data", {}).get("challenge", "")
    )


@router.post("/sms/login")
async def sms_login(req: SMSLoginRequest):
    """短信验证码登录"""
    result = await mhy_api.login_by_mobile_captcha(
        mobile=req.mobile,
        captcha=req.captcha,
        action_type=req.action_type,
        gt=getattr(req, 'gt', ''),
        challenge=getattr(req, 'challenge', ''),
        validate=getattr(req, 'gee_validate', '')
    )

    if result.get("retcode") == 0:
        data = result.get("data", {})
        account = database.add_account(
            name=data.get("name", ""),
            stoken=data.get("stoken", ""),
            uid=data.get("account_id", ""),
            mid=data.get("mid", ""),
            server="官服"
        )
        return {"retcode": 0, "data": account, "message": "登录成功"}

    return {"retcode": result.get("retcode", -1), "message": result.get("message", "登录失败")}


@router.post("/cookie/login")
async def cookie_login(req: CookieLoginRequest):
    """Cookie登录 - 从Cookie中解析SToken和UID"""
    # 解析Cookie
    cookie_str = req.cookie
    cookies = {}
    for item in cookie_str.replace(" ", "").split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            cookies[key] = value
    
    # 查找uid
    uid = cookies.get("stuid") or cookies.get("ltuid") or cookies.get("account_id")
    stoken = cookies.get("stoken")
    mid = cookies.get("mid", "")
    
    if not uid or not stoken:
        return {"retcode": -1, "message": "Cookie格式错误，需要包含stuid/ltuid和stoken"}
    
    name = await mhy_api.get_username_by_uid(uid)
    
    account = database.add_account(
        name=name,
        stoken=stoken,
        uid=uid,
        mid=mid,
        server="官服",
        note=req.note or ""
    )
    return {"retcode": 0, "data": account}
