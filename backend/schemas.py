"""数据模型 - Pydantic schemas"""

from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ServerType(str, Enum):
    OFFICIAL = "官服"
    BH3_BILIBILI = "崩坏3B服"


class GameType(str, Enum):
    BH3 = "bh3"
    GENSHIN = "hk4e"
    HSR = "hkrpg"
    ZZZ = "nap"


class AccountCreate(BaseModel):
    """创建账号请求"""
    name: str
    stoken: str
    uid: str
    mid: Optional[str] = ""
    server: ServerType = ServerType.OFFICIAL
    note: Optional[str] = ""


class AccountUpdate(BaseModel):
    """更新账号请求"""
    name: Optional[str] = None
    stoken: Optional[str] = None
    uid: Optional[str] = None
    mid: Optional[str] = None
    server: Optional[ServerType] = None
    note: Optional[str] = None


class AccountResponse(BaseModel):
    """账号响应"""
    id: int
    name: str
    uid: str
    mid: str
    server: str
    note: str
    created_at: str
    
    class Config:
        from_attributes = True


class QRCodeScanRequest(BaseModel):
    """扫码登录请求"""
    account_id: int
    game: GameType
    ticket: str


class LoginQRCodeResponse(BaseModel):
    """登录二维码响应"""
    url: str
    ticket: str


class SMSSendRequest(BaseModel):
    """发送短信验证码请求"""
    mobile: str
    aigis: str = ""


class SMSLoginRequest(BaseModel):
    """短信验证码登录请求"""
    mobile: str
    captcha: str
    action_type: str = ""
    gt: str = ""
    challenge: str = ""
    gee_validate: str = ""


class CookieLoginRequest(BaseModel):
    """Cookie登录请求"""
    cookie: str
    note: Optional[str] = ""


class CaptchaResponse(BaseModel):
    """验证码响应"""
    retcode: int
    message: str = ""
    action_type: Optional[str] = None
    mmt_type: Optional[int] = None
    gt: Optional[str] = None
    challenge: Optional[str] = None
