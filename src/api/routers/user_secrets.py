from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps_services import get_user_secrets_service
from api.models.user_secrets import CreateSecretPayload, UserSecretResponse
from services.guards import require_active_user
from services.user_secrets_service import UserSecretsService

router = APIRouter(
    prefix="/api/user-secrets",
    tags=["user-secrets"],
)


@router.post("", response_model=UserSecretResponse, status_code=status.HTTP_201_CREATED)
def create_secret(
    payload: CreateSecretPayload,
    user_id: UUID = Depends(require_active_user),
    service: UserSecretsService = Depends(get_user_secrets_service),
):
    secret = service.create(
        actor_id=user_id,
        user_id=user_id,
        type=payload.type,
        secret=payload.secret,
    )
    return secret


@router.get("", response_model=list[UserSecretResponse])
def list_secrets(
    user_id: UUID = Depends(require_active_user),
    service: UserSecretsService = Depends(get_user_secrets_service),
):
    return service.list_for_user(user_id=user_id)


@router.delete("/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_secret(
    secret_id: UUID,
    user_id: UUID = Depends(require_active_user),
    service: UserSecretsService = Depends(get_user_secrets_service),
):
    try:
        service.delete(
            actor_id=user_id,
            user_id=user_id,
            secret_id=secret_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail="Secret not found") from e
