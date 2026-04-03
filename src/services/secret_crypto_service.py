from secrets import token_bytes

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from services.domain.user_secret_vault import (
    DerivedUserKey,
    EncryptedSecretBlob,
    VaultCheckBlob,
)
from services.exceptions import SecretDecryptionFailed

CRYPTO_VERSION = 1

_AES_KEY_BYTES = 32
_AES_GCM_NONCE_BYTES = 12
_ARGON2_SALT_BYTES = 16
_VAULT_CHECK_PLAINTEXT = b"firefly-toolkit:vault-check:v1"
_DEFAULT_KDF_PARAMS = {
    "time_cost": 3,
    "memory_cost": 64 * 1024,
    "parallelism": 2,
    "hash_len": _AES_KEY_BYTES,
}


class SecretCryptoService:
    def derive_user_key(
        self,
        passphrase: str,
        salt: bytes | None = None,
        *,
        params: dict[str, int] | None = None,
    ) -> DerivedUserKey:
        kdf_salt = salt or token_bytes(_ARGON2_SALT_BYTES)
        kdf_params = dict(params or _DEFAULT_KDF_PARAMS)
        key = hash_secret_raw(
            secret=passphrase.encode("utf-8"),
            salt=kdf_salt,
            time_cost=kdf_params["time_cost"],
            memory_cost=kdf_params["memory_cost"],
            parallelism=kdf_params["parallelism"],
            hash_len=kdf_params["hash_len"],
            type=Type.ID,
        )
        return DerivedUserKey(key=key, salt=kdf_salt, params=kdf_params)

    def create_vault_check(self, user_key: bytes) -> VaultCheckBlob:
        nonce = token_bytes(_AES_GCM_NONCE_BYTES)
        # TODO: Add AAD during integration, likely binding user/secret/type/version context.
        ciphertext = AESGCM(user_key).encrypt(
            nonce,
            _VAULT_CHECK_PLAINTEXT,
            associated_data=None,
        )
        return VaultCheckBlob(ciphertext=ciphertext, nonce=nonce)

    def verify_vault_check(self, user_key: bytes, vault_check: VaultCheckBlob) -> bool:
        try:
            plaintext = AESGCM(user_key).decrypt(
                vault_check.nonce,
                vault_check.ciphertext,
                associated_data=None,
            )
        except InvalidTag:
            return False
        return plaintext == _VAULT_CHECK_PLAINTEXT

    def encrypt_secret(self, plaintext: str, user_key: bytes) -> EncryptedSecretBlob:
        dek = token_bytes(_AES_KEY_BYTES)
        secret_nonce = token_bytes(_AES_GCM_NONCE_BYTES)
        wrapped_dek_nonce = token_bytes(_AES_GCM_NONCE_BYTES)
        # TODO: Add AAD during integration, likely binding user/secret/type/version context.
        ciphertext = AESGCM(dek).encrypt(
            secret_nonce,
            plaintext.encode("utf-8"),
            associated_data=None,
        )
        wrapped_dek = AESGCM(user_key).encrypt(
            wrapped_dek_nonce,
            dek,
            associated_data=None,
        )
        return EncryptedSecretBlob(
            ciphertext=ciphertext,
            secret_nonce=secret_nonce,
            wrapped_dek=wrapped_dek,
            wrapped_dek_nonce=wrapped_dek_nonce,
            crypto_version=CRYPTO_VERSION,
        )

    def decrypt_secret(self, blob: EncryptedSecretBlob, user_key: bytes) -> str:
        if blob.crypto_version != CRYPTO_VERSION:
            raise ValueError(f"Unsupported crypto_version: {blob.crypto_version}")
        try:
            dek = AESGCM(user_key).decrypt(
                blob.wrapped_dek_nonce,
                blob.wrapped_dek,
                associated_data=None,
            )
            plaintext = AESGCM(dek).decrypt(
                blob.secret_nonce,
                blob.ciphertext,
                associated_data=None,
            )
        except InvalidTag as exc:
            raise SecretDecryptionFailed("Secret decryption failed") from exc
        return plaintext.decode("utf-8")
