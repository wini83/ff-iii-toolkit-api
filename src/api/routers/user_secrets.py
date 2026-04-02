from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.deps_services import (
    get_user_secrets_service,
    get_vault_service,
    get_vault_session_id,
)
from api.models.user_secrets import (
    CreateSecretPayload,
    UpdateSecretPayload,
    UserSecretResponse,
    VaultPassphrasePayload,
    VaultStatusResponse,
)
from services.exceptions import (
    InvalidVaultPassphrase,
    SecretDecryptionFailed,
    SecretNotAccessible,
    VaultAlreadyConfigured,
    VaultLocked,
    VaultNotConfigured,
    VaultSessionExpired,
)
from services.guards import require_active_user
from services.user_secrets_service import UserSecretsService
from services.vault_service import VaultService
from settings import settings

router = APIRouter(
    prefix="/api/user-secrets",
    tags=["user-secrets"],
    dependencies=[Depends(require_active_user)],
)


def _raise_user_secret_http_error(exc: Exception) -> None:
    if isinstance(exc, SecretNotAccessible):
        raise HTTPException(status_code=404, detail="Secret not found") from exc
    if isinstance(exc, VaultAlreadyConfigured):
        raise HTTPException(status_code=409, detail="Vault already configured") from exc
    if isinstance(exc, VaultNotConfigured):
        raise HTTPException(status_code=409, detail="Vault not configured") from exc
    if isinstance(exc, InvalidVaultPassphrase):
        raise HTTPException(status_code=401, detail="Invalid vault passphrase") from exc
    if isinstance(exc, VaultLocked):
        raise HTTPException(status_code=423, detail="Vault is locked") from exc
    if isinstance(exc, VaultSessionExpired):
        raise HTTPException(status_code=401, detail="Vault session expired") from exc
    if isinstance(exc, SecretDecryptionFailed):
        raise HTTPException(status_code=422, detail="Secret decryption failed") from exc
    raise exc


def _set_vault_session_cookie(response: Response, vault_session_id: str) -> None:
    response.set_cookie(
        settings.VAULT_SESSION_COOKIE_NAME,
        vault_session_id,
        httponly=True,
        secure=settings.VAULT_SESSION_SECURE,
        samesite="lax",
        max_age=settings.VAULT_SESSION_TTL_SECONDS,
        path="/",
    )


def _clear_vault_session_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.VAULT_SESSION_COOKIE_NAME,
        path="/",
    )


@router.post("/vault/setup", response_model=VaultStatusResponse)
def setup_vault(
    payload: VaultPassphrasePayload,
    user_id: UUID = Depends(require_active_user),
    service: VaultService = Depends(get_vault_service),
):
    try:
        service.setup_vault(user_id, payload.passphrase)
    except (
        VaultAlreadyConfigured,
        VaultNotConfigured,
        InvalidVaultPassphrase,
        VaultLocked,
        VaultSessionExpired,
        SecretDecryptionFailed,
        SecretNotAccessible,
    ) as exc:
        _raise_user_secret_http_error(exc)
    return VaultStatusResponse(configured=True, unlocked=False)


@router.post("/vault/unlock", response_model=VaultStatusResponse)
def unlock_vault(
    payload: VaultPassphrasePayload,
    response: Response,
    user_id: UUID = Depends(require_active_user),
    service: VaultService = Depends(get_vault_service),
):
    try:
        vault_session_id = service.unlock_vault(user_id, payload.passphrase)
    except (
        VaultAlreadyConfigured,
        VaultNotConfigured,
        InvalidVaultPassphrase,
        VaultLocked,
        VaultSessionExpired,
        SecretDecryptionFailed,
        SecretNotAccessible,
    ) as exc:
        _raise_user_secret_http_error(exc)

    _set_vault_session_cookie(response, vault_session_id)
    return VaultStatusResponse(configured=True, unlocked=True)


@router.post("/vault/lock", response_model=VaultStatusResponse)
def lock_vault(
    response: Response,
    user_id: UUID = Depends(require_active_user),
    vault_session_id: str | None = Depends(get_vault_session_id),
    service: VaultService = Depends(get_vault_service),
):
    if vault_session_id is not None:
        service.lock_vault(user_id, vault_session_id)
    _clear_vault_session_cookie(response)
    return VaultStatusResponse(
        configured=service.is_configured(user_id),
        unlocked=False,
    )


@router.get("/vault/status", response_model=VaultStatusResponse)
def get_vault_status(
    user_id: UUID = Depends(require_active_user),
    vault_session_id: str | None = Depends(get_vault_session_id),
    service: VaultService = Depends(get_vault_service),
):
    configured = service.is_configured(user_id)
    unlocked = configured and service.is_unlocked(user_id, vault_session_id)
    return VaultStatusResponse(configured=configured, unlocked=unlocked)


@router.post("", response_model=UserSecretResponse, status_code=status.HTTP_201_CREATED)
def create_secret(
    payload: CreateSecretPayload,
    user_id: UUID = Depends(require_active_user),
    vault_session_id: str | None = Depends(get_vault_session_id),
    service: UserSecretsService = Depends(get_user_secrets_service),
):
    """Create an encrypted secret; plaintext is never returned from this API."""
    try:
        secret = service.create_secret(
            actor_id=user_id,
            user_id=user_id,
            vault_session_id=vault_session_id,
            type=payload.type,
            alias=payload.alias,
            external_username=payload.external_username,
            secret=payload.secret,
        )
        return secret
    except (
        VaultAlreadyConfigured,
        VaultNotConfigured,
        InvalidVaultPassphrase,
        VaultLocked,
        VaultSessionExpired,
        SecretDecryptionFailed,
        SecretNotAccessible,
    ) as exc:
        _raise_user_secret_http_error(exc)


@router.get("", response_model=list[UserSecretResponse])
def list_secrets(
    user_id: UUID = Depends(require_active_user),
    service: UserSecretsService = Depends(get_user_secrets_service),
):
    """Return secret metadata only; no plaintext reveal endpoint is exposed."""
    return service.list_for_user(user_id=user_id)


@router.patch("/{secret_id}", response_model=UserSecretResponse)
def update_secret(
    secret_id: UUID,
    payload: UpdateSecretPayload,
    user_id: UUID = Depends(require_active_user),
    vault_session_id: str | None = Depends(get_vault_session_id),
    service: UserSecretsService = Depends(get_user_secrets_service),
):
    try:
        return service.update_secret(
            actor_id=user_id,
            user_id=user_id,
            secret_id=secret_id,
            vault_session_id=vault_session_id,
            alias=payload.alias if "alias" in payload.model_fields_set else ...,
            external_username=(
                payload.external_username
                if "external_username" in payload.model_fields_set
                else ...
            ),
            secret=payload.secret if "secret" in payload.model_fields_set else ...,
        )
    except (
        VaultAlreadyConfigured,
        VaultNotConfigured,
        InvalidVaultPassphrase,
        VaultLocked,
        VaultSessionExpired,
        SecretDecryptionFailed,
        SecretNotAccessible,
    ) as exc:
        _raise_user_secret_http_error(exc)


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
    except (
        VaultAlreadyConfigured,
        VaultNotConfigured,
        InvalidVaultPassphrase,
        VaultLocked,
        VaultSessionExpired,
        SecretDecryptionFailed,
        SecretNotAccessible,
    ) as exc:
        _raise_user_secret_http_error(exc)
