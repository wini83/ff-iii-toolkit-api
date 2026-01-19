from passlib.context import CryptContext

_pwd = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__time_cost=3,  # CPU work factor
    argon2__memory_cost=64 * 1024,  # 64 MB RAM
    argon2__parallelism=2,
)


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd.verify(password, password_hash)
