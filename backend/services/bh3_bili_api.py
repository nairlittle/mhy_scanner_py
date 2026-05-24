"""BSGameSDK - 崩坏3 Bilibili(B服) 账号登录
对齐原版 C++ BSGameSDK.hpp
"""

import json
import time
import urllib.parse

import httpx

from .crypto import md5, rsa_encrypt

# === Bilibili游戏SDK API ===
BILI_SDK_BASE = "https://line1-sdk-center-login-sh.biligame.net"

BILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 BSGameSDK",
    "Content-Type": "application/x-www-form-urlencoded",
    "Host": "line1-sdk-center-login-sh.biligame.net",
}

# 固定参数（对齐原版BSGameSDK.hpp）
_DEVICE_PARAMS = {
    "operators": "5",
    "merchant_id": "590",
    "isRoot": "0",
    "domain_switch_count": "0",
    "sdk_type": "1",
    "sdk_log_type": "1",
    "support_abis": "x86,armeabi-v7a,armeabi",
    "access_key": "",
    "sdk_ver": "3.4.2",
    "oaid": "",
    "dp": "1280*720",
    "original_domain": "",
    "imei": "",
    "version": "1",
    "udid": "KREhESMUIhUjFnJKNko2TDQFYlZkB3cdeQ==",
    "apk_sign": "4502a02a00395dec05a4134ad593224d",
    "platform_type": "3",
    "old_buvid": "XZA2FA4AC240F665E2F27F603ABF98C615C29",
    "android_id": "84567e2dda72d1d4",
    "fingerprint": "",
    "mac": "08:00:27:53:DD:12",
    "server_id": "378",
    "domain": "line1-sdk-center-login-sh.biligame.net",
    "app_id": "180",
    "version_code": "510",
    "net": "4",
    "pf_ver": "12",
    "cur_buvid": "XZA2FA4AC240F665E2F27F603ABF98C615C29",
    "c": "1",
    "brand": "Android",
    "channel_id": "1",
    "game_id": "180",
    "ver": "6.1.0",
    "model": "MuMu",
}

# 签名密钥（对齐原版签名算法）
SIGN_SALT = "dbf8f1b4496f430b8a3c0f436a35b931"


def _get_timestamp():
    """获取Unix时间戳（毫秒）"""
    t = int(time.time() * 1000)
    return str(t)


def _sign_and_build_body(params: dict) -> str:
    """对齐原版 SetSign 算法：用所有value拼接后加salt做MD5签名"""
    # 更新时间戳
    ts = _get_timestamp()
    params["timestamp"] = ts
    params["client_timestamp"] = ts

    sign_str = ""
    body_parts = []

    for key in params:
        value = params[key]
        sign_str += str(value)
        if key == "pwd":
            body_parts.append(f"{key}={urllib.parse.quote(str(value))}&")
        else:
            body_parts.append(f"{key}={value}&")

    sign_str += SIGN_SALT
    body = "".join(body_parts)
    body += f"sign={md5(sign_str)}"
    return body


async def _post_bili(url: str, body: str) -> dict:
    """发送Bilibili游戏SDK请求"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, content=body, headers=BILI_HEADERS)
        return resp.json()


async def get_rsa_key() -> dict:
    """获取RSA公钥和hash（用于加密密码）"""
    params = dict(_DEVICE_PARAMS)
    body = _sign_and_build_body(params)

    rsp = await _post_bili(f"{BILI_SDK_BASE}/api/client/rsa", body)
    return {
        "rsa_key": rsp.get("rsa_key", ""),
        "hash": rsp.get("hash", ""),
    }


async def get_encrypted_password(password: str) -> str:
    """获取RSA加密后的密码"""
    rsa_info = await get_rsa_key()
    public_key = rsa_info["rsa_key"]
    hash_val = rsa_info["hash"]
    combined = hash_val + password
    return rsa_encrypt(combined, public_key)


async def start_captcha() -> dict:
    """获取GeeTest验证码参数"""
    params = dict(_DEVICE_PARAMS)
    body = _sign_and_build_body(params)

    rsp = await _post_bili(f"{BILI_SDK_BASE}/api/client/start_captcha", body)
    return {
        "gt": rsp.get("gt", ""),
        "challenge": rsp.get("challenge", ""),
        "gt_user_id": rsp.get("gt_user_id", ""),
    }


async def login_by_password(
    account: str,
    password: str,
    gt_user_id: str = "",
    challenge: str = "",
    validate: str = "",
    seccode: str = "",
) -> dict:
    """Bilibili游戏SDK密码登录

    Returns:
        {"code": 0, "uid": str, "access_key": str, "uname": str}
        or {"code": -1, "message": str}
    """
    params = dict(_DEVICE_PARAMS)
    params["access_key"] = ""
    params["gt_user_id"] = gt_user_id
    params["uid"] = ""
    params["challenge"] = challenge
    params["user_id"] = account
    params["validate"] = validate

    if validate:
        params["seccode"] = str(validate) + "|jordan"

    # 加密密码
    params["pwd"] = await get_encrypted_password(password)

    body = _sign_and_build_body(params)
    rsp = await _post_bili(f"{BILI_SDK_BASE}/api/client/login", body)

    code = rsp.get("code", -1)
    if code == 20000 or code != 0:
        return {"code": -1, "message": rsp.get("message", "登录失败")}

    uid = str(rsp.get("uid", 0))
    access_key = rsp.get("access_key", "")

    # 获取用户信息
    uname = await get_user_info_by_bili(uid, access_key)

    return {
        "code": 0,
        "uid": uid,
        "access_key": access_key,
        "uname": uname or account,
    }


async def get_user_info_by_bili(uid: str, access_key: str) -> str:
    """通过Bilibili SDK获取用户名"""
    params = dict(_DEVICE_PARAMS)
    params["uid"] = uid
    params["access_key"] = access_key

    body = _sign_and_build_body(params)
    rsp = await _post_bili(f"{BILI_SDK_BASE}/api/client/user.info", body)

    if rsp.get("code") != 0:
        return ""
    return rsp.get("uname", "")
