"""加密工具模块 - HMAC-SHA256、MD5、纯Python RSA加密"""

import hashlib
import hmac
import base64
import os
import struct


def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def hmac_sha256(message: str, key: str) -> str:
    mac = hmac.new(key.encode(), message.encode(), hashlib.sha256)
    return mac.hexdigest()


# === 纯Python RSA PKCS1v15 加密 ===

def _parse_pem_public_key(pem: str) -> tuple[int, int]:
    """从PEM格式公钥解析出(n, e)"""
    b64 = pem.replace("-----BEGIN PUBLIC KEY-----", "").replace("-----END PUBLIC KEY-----", "").replace("\n", "").replace("\r", "")
    der = base64.b64decode(b64)

    # DER 结构: SEQUENCE { SEQUENCE { OID, NULL }, BIT STRING { SEQUENCE { INTEGER n, INTEGER e } } }
    pos = 0

    def read_byte():
        nonlocal pos
        b = der[pos]
        pos += 1
        return b

    def read_length():
        nonlocal pos
        b = der[pos]
        pos += 1
        if b < 0x80:
            return b
        num_bytes = b & 0x7F
        length = int.from_bytes(der[pos:pos+num_bytes], "big")
        pos += num_bytes
        return length

    def read_integer():
        nonlocal pos
        tag = read_byte()  # 0x02
        length = read_length()
        val = int.from_bytes(der[pos:pos+length], "big")
        pos += length
        return val

    # 外层 SEQUENCE
    read_byte()  # tag 0x30
    read_length()
    # 内层 AlgorithmIdentifier SEQUENCE
    read_byte()  # tag 0x30
    alg_len = read_length()
    pos += alg_len  # 跳过 OID + NULL
    # BIT STRING
    read_byte()  # tag 0x03
    bit_len = read_length()
    pos += 1  # 跳过 unused bits 字节
    # 最内层 SEQUENCE { n, e }
    read_byte()  # tag 0x30
    read_length()
    n = read_integer()
    e = read_integer()
    return n, e


def _pkcs1v15_pad(message: bytes, key_size: int) -> bytes:
    """PKCS#1 v1.5 填充 (Type 2)"""
    max_mlen = key_size - 11
    if len(message) > max_mlen:
        raise ValueError(f"消息过长: {len(message)} > {max_mlen}")
    ps_len = key_size - 3 - len(message)
    ps = bytearray()
    while len(ps) < ps_len:
        b = os.urandom(1)[0]
        if b != 0:
            ps.append(b)
    return b"\x00\x02" + bytes(ps) + b"\x00" + message


def rsa_encrypt(message: str, public_key_pem: str) -> str:
    """RSA公钥加密（PKCS1v15填充），返回Base64密文"""
    n, e = _parse_pem_public_key(public_key_pem)
    key_size = (n.bit_length() + 7) // 8
    padded = _pkcs1v15_pad(message.encode(), key_size)
    m = int.from_bytes(padded, "big")
    c = pow(m, e, n)
    ciphertext = c.to_bytes(key_size, "big")
    return base64.b64encode(ciphertext).decode()
