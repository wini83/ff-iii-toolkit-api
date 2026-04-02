from dataclasses import replace

import pytest

from services.domain.user_secret_vault import VaultCheckBlob
from services.exceptions import SecretDecryptionFailed
from services.secret_crypto_service import CRYPTO_VERSION, SecretCryptoService


def test_derive_user_key_uses_explicit_params_and_salt():
    service = SecretCryptoService()
    salt = b"0123456789abcdef"
    params = {
        "time_cost": 2,
        "memory_cost": 32 * 1024,
        "parallelism": 1,
        "hash_len": 32,
    }

    derived = service.derive_user_key("passphrase", salt, params=params)

    assert derived.salt == salt
    assert derived.params == params
    assert isinstance(derived.key, bytes)
    assert len(derived.key) == 32


def test_vault_check_verification_returns_false_for_wrong_key():
    service = SecretCryptoService()
    correct_key = service.derive_user_key("passphrase").key
    wrong_key = service.derive_user_key("other-passphrase").key
    blob = service.create_vault_check(correct_key)

    assert service.verify_vault_check(correct_key, blob) is True
    assert service.verify_vault_check(wrong_key, blob) is False


def test_vault_check_verification_returns_false_for_tampered_blob():
    service = SecretCryptoService()
    user_key = service.derive_user_key("passphrase").key
    blob = service.create_vault_check(user_key)
    tampered = VaultCheckBlob(
        ciphertext=blob.ciphertext[:-1] + b"\x00", nonce=blob.nonce
    )

    assert service.verify_vault_check(user_key, tampered) is False


def test_encrypt_and_decrypt_secret_roundtrip():
    service = SecretCryptoService()
    user_key = service.derive_user_key("passphrase").key

    blob = service.encrypt_secret("sekret", user_key)

    assert blob.crypto_version == CRYPTO_VERSION
    assert service.decrypt_secret(blob, user_key) == "sekret"


def test_decrypt_secret_raises_for_unsupported_crypto_version():
    service = SecretCryptoService()
    user_key = service.derive_user_key("passphrase").key
    blob = service.encrypt_secret("sekret", user_key)

    with pytest.raises(ValueError, match="Unsupported crypto_version"):
        service.decrypt_secret(replace(blob, crypto_version=999), user_key)


def test_decrypt_secret_raises_project_exception_for_wrong_user_key():
    service = SecretCryptoService()
    user_key = service.derive_user_key("passphrase").key
    other_key = service.derive_user_key("other-passphrase").key
    blob = service.encrypt_secret("sekret", user_key)

    with pytest.raises(SecretDecryptionFailed, match="Secret decryption failed"):
        service.decrypt_secret(blob, other_key)
