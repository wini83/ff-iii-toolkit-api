from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class DerivedUserKey:
    key: bytes
    salt: bytes
    params: dict[str, int]


@dataclass(slots=True, frozen=True)
class VaultCheckBlob:
    ciphertext: bytes
    nonce: bytes


@dataclass(slots=True, frozen=True)
class EncryptedSecretBlob:
    ciphertext: bytes
    secret_nonce: bytes
    wrapped_dek: bytes
    wrapped_dek_nonce: bytes
    crypto_version: int
