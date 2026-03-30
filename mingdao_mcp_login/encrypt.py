# -*- coding: utf-8 -*-
"""RSA 加密账号与密码（与明道云登录页约定一致：先 URL 编码再 PKCS#1 v1.5 加密）。"""

import base64
import urllib.parse

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC1xzCYtdu8bZEinh6Oh7/p+6xc
ilHgV/ChU3bZXyezLQqf6mzOnLH6GVZMMDafMw3uMtljWyECCqnECy2UhZPa5BFc
qA2xbYH8/WyKTraCRJT3Hn61UrI4Eac4YVxa1CJ8KaTQtIeZBoXHIW0r5XyhBwYe
NkSun+OFN+YBoJvCXwIDAQAB
-----END PUBLIC KEY-----"""


def encrypt(text: str, public_key: str = PUBLIC_KEY) -> str:
    key = RSA.import_key(public_key)
    cipher = PKCS1_v1_5.new(key)
    encoded_text = urllib.parse.quote(text)
    encrypted_bytes = cipher.encrypt(encoded_text.encode("utf-8"))
    return base64.b64encode(encrypted_bytes).decode("utf-8")
