import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet, InvalidToken


class WrongPassword(Exception):
    pass


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt(data: bytes, password: str) -> bytes:
    salt = os.urandom(16)
    key = derive_key(password, salt)
    f = Fernet(key)
    return salt + f.encrypt(data)


def decrypt(data: bytes, password: str) -> bytes:
    try:
        salt = data[:16]
        token = data[16:]
        key = derive_key(password, salt)
        f = Fernet(key)
        return f.decrypt(token)
    except Exception:
        raise WrongPassword("Incorrect password")
