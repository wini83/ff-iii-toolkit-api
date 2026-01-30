from services.db.repository import UserRepository


class BootstrapAlreadyDone(Exception):
    pass


class BootstrapService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def is_bootstrapped(self) -> bool:
        return self.user_repo.count_users() > 0

    def bootstrap_superuser(self, username: str, password_hash: str) -> None:
        if self.is_bootstrapped():
            raise BootstrapAlreadyDone("System already bootstrapped")

        self.user_repo.create(
            username=username,
            password_hash=password_hash,
            is_superuser=True,
        )
