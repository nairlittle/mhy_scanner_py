"""加密工具模块 - RSA加密、HMAC-SHA256、MD5"""

import hashlib
import hmac
import base64

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


def rsa_encrypt(message: str, public_key_pem: str) -> str:
    """RSA公钥加密，返回Base64编码的密文"""
    public_key = serialization.load_pem_public_key(
        public_key_pem.encode(), backend=default_backend()
    )
    encrypted = public_key.encrypt(
        message.encode(),
        padding.PKCS1v15()
    )
    return base64.b64encode(encrypted).decode()


def hmac_sha256(message: str, key: str) -> str:
    """HMAC-SHA256，返回十六进制字符串"""
    mac = hmac.new(key.encode(), message.encode(), hashlib.sha256)
    return mac.hexdigest()


def md5(s: str) -> str:
    """MD5哈希，返回十六进制字符串"""
    return hashlib.md5(s.encode()).hexdigest()
