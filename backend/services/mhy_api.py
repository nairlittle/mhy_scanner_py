"""米哈游API客户端 - 扫码登录、SToken获取、验证码登录等"""

import time
import uuid
import random
import hashlib
import json
import io
import base64
from typing import Optional

import httpx
import qrcode

from .crypto import rsa_encrypt, hmac_sha256, md5

# === 常量 ===
APP_VERSION = "2.76.1"
SALT_X6 = "t0qEgfub6cvueAPgR5m9aQWWVciEer7v"

API_SDK = "https://api-sdk.mihoyo.com"
PASSPORT_API = "https://passport-api.mihoyo.com"
TAKUMI_API = "https://api-takumi.mihoyo.com"
BBS_API = "https://bbs-api.miyoushe.com"

# 各游戏的SDK域名
GAME_SDK_HOSTS = {
    "bh3": "https://api-sdk.mihoyo.com/bh3_cn",
    "hk4e": "https://hk4e-sdk.mihoyo.com/hk4e_cn",
    "hkrpg": "https://api-sdk.mihoyo.com/hkrpg_cn",
    "nap": "https://api-sdk.mihoyo.com/nap_cn",
}

# scan/confirm 接口使用 api-sdk 域名（对齐原版：hk4e的scan/confirm不走hk4e-sdk）
GAME_API_HOSTS = {
    "bh3": "https://api-sdk.mihoyo.com/bh3_cn",
    "hk4e": "https://api-sdk.mihoyo.com/hk4e_cn",
    "hkrpg": "https://api-sdk.mihoyo.com/hkrpg_cn",
    "nap": "https://api-sdk.mihoyo.com/nap_cn",
}

# 游戏 app_id 映射
GAME_APP_IDS = {
    "bh3": 1,
    "hk4e": 4,
    "hkrpg": 8,
    "nap": 12,
}

BBS_APP_ID = 2  # 米游社BBS扫码登录使用TearsOfThemis的app_id

DEVICE_ID = str(uuid.uuid4()).upper()


def _url_to_qrcode_dataurl(url: str) -> str:
    """将URL文本生成QR码PNG图片的base64 data URL"""
    img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"


def _get_game_sdk_host(game: str) -> str:
    """获取游戏SDK域名（fetch/query接口）"""
    return GAME_SDK_HOSTS.get(game, GAME_SDK_HOSTS["hk4e"])


def _get_game_api_host(game: str) -> str:
    """获取游戏API域名（scan/confirm接口，对齐原版：hk4e用api-sdk非hk4e-sdk）"""
    return GAME_API_HOSTS.get(game, GAME_API_HOSTS["hk4e"])


def _detect_game_from_qr_url(qr_url: str) -> str:
    """从QR码URL中检测游戏类型"""
    if "/hk4e_cn/" in qr_url or "hk4e-sdk" in qr_url:
        return "hk4e"
    if "/hkrpg_cn/" in qr_url:
        return "hkrpg"
    if "/bh3_cn/" in qr_url:
        return "bh3"
    if "/nap_cn/" in qr_url:
        return "nap"
    return "hk4e"


def _generate_ds(body: str = "", query: str = "") -> str:
    """生成米哈游API所需的DS签名"""
    t = str(int(time.time()))
    r = str(random.randint(100001, 200000))
    s = f"salt={SALT_X6}&t={t}&r={r}&b={body}&q={query}"
    c = md5(s)
    return f"{t},{r},{c}"


def _get_request_headers() -> dict:
    """获取标准请求头"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) miHoYoBBS/2.76.1",
        "Accept": "application/json",
        "x-rpc-app_id": "bll8iq97cem8",
        "x-rpc-app_version": APP_VERSION,
        "x-rpc-client_type": "2",
        "x-rpc-device_id": DEVICE_ID,
        "x-rpc-device_name": "",
        "x-rpc-game_biz": "bbs_cn",
        "x-rpc-sdk_version": "2.16.0",
    }


def _api_post(url: str, body: dict, ds_body: str = "", ds_query: str = "") -> dict:
    """生成需要DS签名的POST请求头"""
    headers = _get_request_headers()
    headers["DS"] = _generate_ds(body=ds_body, query=ds_query)
    headers["Content-Type"] = "application/json"
    return headers


# ============ 登录二维码 ============

async def get_login_qrcode_url() -> tuple[str, str]:
    """获取米游社BBS登录二维码（返回图片data URL和ticket）

    对齐原版: 使用 TearsOfThemis (app_id=2) 作为BBS扫码登录
    """
    body_dict = {"app_id": BBS_APP_ID, "device": DEVICE_ID}
    host = _get_game_sdk_host("hk4e")  # BBS登录复用hk4e的fetch/query接口

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{host}/combo/panda/qrcode/fetch",
            json=body_dict,
            headers={"Content-Type": "application/json"}
        )
        data = resp.json()
        if data.get("retcode") != 0:
            raise Exception(f"获取二维码失败: {data.get('message', '未知错误')}")

        url = data["data"]["url"]
        # 对齐原版: ticket = url最后24个字符
        ticket = url[-24:] if len(url) >= 24 else url
        qr_img = _url_to_qrcode_dataurl(url)
        return qr_img, ticket


async def check_qrcode_state(ticket: str) -> dict:
    """查询BBS登录二维码扫描状态

    对齐原版: 使用 BBS_APP_ID(2) 查询
    """
    body_dict = {"app_id": BBS_APP_ID, "device": DEVICE_ID, "ticket": ticket}
    host = _get_game_sdk_host("hk4e")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{host}/combo/panda/qrcode/query",
            json=body_dict,
            headers={"Content-Type": "application/json"}
        )
        data = resp.json()
        if data.get("retcode") != 0:
            return {"stat": "Expired"}

        stat = data["data"].get("stat", "Expired")
        if stat not in ("Init", "Scanned", "Confirmed"):
            stat = "Expired"

        result = {"stat": stat}
        if stat == "Confirmed":
            raw = data["data"]["payload"]["raw"]
            payload = json.loads(raw)
            result["game_token"] = payload.get("token", "")
            result["uid"] = payload.get("uid", "")

        return result


async def get_stoken_by_game_token(uid: str, game_token: str) -> dict:
    """通过GameToken获取SToken和mid"""
    body_json = json.dumps({"account_id": int(uid), "game_token": game_token})
    headers = _api_post(
        f"{TAKUMI_API}/account/ma-cn-session/app/getTokenByGameToken",
        {"account_id": int(uid), "game_token": game_token},
        ds_body=body_json
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TAKUMI_API}/account/ma-cn-session/app/getTokenByGameToken",
            json={"account_id": int(uid), "game_token": game_token},
            headers=headers
        )
        data = resp.json()
        if data.get("retcode") != 0:
            return {"retcode": -1, "message": data.get("message", "获取SToken失败")}

        stoken = data["data"]["token"]["token"]
        mid = data["data"]["user_info"]["mid"]
        return {"retcode": 0, "stoken": stoken, "mid": mid}


async def get_username_by_uid(uid: str) -> str:
    """通过UID获取用户名"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BBS_API}/user/api/getUserFullInfo",
            params={"uid": uid}
        )
        try:
            data = resp.json()
            if data.get("retcode") == 0:
                return data["data"]["user_info"]["nickname"]
        except Exception:
            pass
        return uid


async def get_game_token_by_stoken(stoken: str, mid: str) -> str:
    """通过SToken获取游戏game_token（用于confirm payload）"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{TAKUMI_API}/auth/api/getGameToken",
            params={"stoken": stoken, "mid": mid}
        )
        data = resp.json()
        if data.get("retcode") != 0:
            raise Exception(f"获取game_token失败: {data.get('message', '')}")
        return data["data"]["game_token"]


# ============ 游戏扫码确认 ============

async def qrcode_scan(
    game: str,
    ticket: str,
    stoken: str,
    uid: str,
    mid: str,
    server: str = "官服"
) -> dict:
    """游戏扫码登录 - scan + confirm

    对齐原版: 先获取game_token，scan成功后用 uid+token 构造payload调用confirm
    """
    app_id = GAME_APP_IDS.get(game, 4)
    host = _get_game_api_host(game)

    headers = _get_request_headers()
    headers["Content-Type"] = "application/json"

    if server == "崩坏3B服":
        headers["Cookie"] = f"stuid={uid};access_key={stoken};mid={mid}"
    else:
        headers["Cookie"] = f"stuid={uid};stoken={stoken};mid={mid}"

    # 步骤0: 获取game_token
    try:
        game_token = await get_game_token_by_stoken(stoken, mid)
        print(f"[SCAN] game_token获取成功: {game_token[:30]}...")
    except Exception as e:
        return {"retcode": -1, "message": f"获取game_token失败: {str(e)}"}

    async with httpx.AsyncClient() as client:
        # 步骤1: scan
        scan_resp = await client.post(
            f"{host}/combo/panda/qrcode/scan",
            json={"app_id": app_id, "device": DEVICE_ID, "ticket": ticket},
            headers=headers
        )
        scan_data = scan_resp.json()
        if scan_data.get("retcode") != 0:
            return {"retcode": -1, "message": f"扫码失败: {scan_data.get('message', '')}"}

        # 步骤2: confirm - 构造payload (对齐原版ConfirmQRLogin)
        raw_payload = json.dumps({"uid": uid, "token": game_token})
        confirm_body = {
            "app_id": app_id,
            "device": DEVICE_ID,
            "ticket": ticket,
            "payload": {
                "proto": "Account",
                "raw": raw_payload
            }
        }

        confirm_resp = await client.post(
            f"{host}/combo/panda/qrcode/confirm",
            json=confirm_body,
            headers=headers
        )
        confirm_data = confirm_resp.json()

        if confirm_data.get("retcode") == 0:
            return {"retcode": 0, "message": "扫码登录成功"}

        return {"retcode": -1, "message": f"确认失败: {confirm_data.get('message', '')}"}


# ============ 短信验证码登录 ============

RSA_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDDvekdPMHN3AYhm/vktJT+YJr7
cI5DcsNKqdsx5DZX0gDuWFuIjzdwButrIYPNmRJ1G8ybDIF7oDW2eEpm5sMbL9zs
9ExXCdvqrn51qELbqj0XxtMTIpaCHFSI50PfPpTFV9Xt/hmyVwokoOXFlAEgCn+Q
CgGs52bFoYMtyi+xEQIDAQAB
-----END PUBLIC KEY-----"""

GEE_TEST_PRODUCT_ID = "4a1cb4a6f425a1e59e8ddcfc27e3db2c"


async def create_login_captcha(mobile: str, aigis: str = "") -> dict:
    """创建登录验证码（发送短信验证码）"""
    body_dict = {
        "area_code": rsa_encrypt("+86", RSA_PUBLIC_KEY),
        "mobile": rsa_encrypt(mobile, RSA_PUBLIC_KEY)
    }
    body_str = json.dumps(body_dict)
    headers = _api_post(
        f"{PASSPORT_API}/account/ma-cn-verifier/verifier/createLoginCaptcha",
        body_dict,
        ds_body=body_str
    )

    if aigis:
        headers["x-rpc-aigis"] = aigis

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PASSPORT_API}/account/ma-cn-verifier/verifier/createLoginCaptcha",
            json=body_dict,
            headers=headers
        )
        return resp.json()


async def login_by_mobile_captcha(
    mobile: str,
    captcha: str,
    action_type: str = "",
    gt: str = "",
    challenge: str = "",
    validate: str = ""
) -> dict:
    """短信验证码登录"""
    body_dict = {
        "area_code": rsa_encrypt("+86", RSA_PUBLIC_KEY),
        "mobile": rsa_encrypt(mobile, RSA_PUBLIC_KEY),
        "captcha": captcha,
        "action_type": action_type,
    }

    body_str = json.dumps(body_dict)
    login_headers = _api_post(
        f"{PASSPORT_API}/account/ma-cn-passport/app/loginByMobileCaptcha",
        body_dict,
        ds_body=body_str
    )

    if gt and challenge:
        login_headers["x-rpc-validate"] = validate
        login_headers["x-rpc-challenge_game"] = "2"
        login_headers["x-rpc-challenge_path"] = (
            f"https://www.geetest.com/adaptive-captcha-demo/v3/geetest?appid={GEE_TEST_PRODUCT_ID}"
        )
        login_headers["x-rpc-page"] = login_headers["x-rpc-challenge_path"]
        login_headers["x-rpc-challenge_source"] = "geetest"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PASSPORT_API}/account/ma-cn-passport/app/loginByMobileCaptcha",
            json=body_dict,
            headers=login_headers
        )
        data = resp.json()

        if data.get("retcode") == 0:
            payload = data.get("data", {})
            token_info = payload.get("token", {})

            return {
                "retcode": 0,
                "data": {
                    "account_id": str(payload.get("account_id", "")),
                    "stoken": token_info.get("token", ""),
                    "mid": str(payload.get("user_info", {}).get("mid", "")),
                    "name": payload.get("user_info", {}).get("nickname", ""),
                }
            }

        return {
            "retcode": data.get("retcode", -1),
            "message": data.get("message", "登录失败"),
            "data": data.get("data", {}),
        }
