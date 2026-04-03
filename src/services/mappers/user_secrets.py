from services.db.models import UserSecretORM
from services.domain.user_secrets import UserSecretReadModel


def map_secret_to_domain_read_model(obj: UserSecretORM) -> UserSecretReadModel:
    return UserSecretReadModel(
        id=obj.id,
        type=obj.type,
        alias=obj.alias,
        external_username=getattr(obj, "external_username", None),
        usage_count=obj.usage_count,
        last_used_at=obj.last_used_at,
        created_at=obj.created_at,
    )


def map_secrets_to_domain_read_models(
    objs: list[UserSecretORM],
) -> list[UserSecretReadModel]:
    return [
        UserSecretReadModel(
            id=obj.id,
            type=obj.type,
            alias=obj.alias,
            external_username=getattr(obj, "external_username", None),
            usage_count=obj.usage_count,
            last_used_at=obj.last_used_at,
            created_at=obj.created_at,
        )
        for obj in objs
    ]
