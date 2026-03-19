from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_pwd = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,  # 64 MB
    parallelism=2,
)


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _pwd.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
