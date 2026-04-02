class ApplicationError(Exception):
    """Base class for all application-level errors."""


# ---- 4xx ----
class InvalidFileId(ApplicationError):
    pass


class InvalidFileFormat(ApplicationError):
    pass


class FileNotFound(ApplicationError):
    pass


class MatchesNotComputed(ApplicationError):
    pass


class InvalidMatchSelection(ApplicationError):
    pass


class TransactionNotFound(ApplicationError):
    pass


class InvalidSecretId(ApplicationError):
    pass


class SecretNotAccessible(ApplicationError):
    """Secret does not exist or is not available to the current user."""


class VaultNotConfigured(ApplicationError):
    pass


class VaultAlreadyConfigured(ApplicationError):
    pass


class VaultLocked(ApplicationError):
    pass


class VaultSessionExpired(ApplicationError):
    pass


class InvalidVaultPassphrase(ApplicationError):
    pass


class SecretDecryptionFailed(ApplicationError):
    pass


# ---- 5xx ----
class ExternalServiceFailed(ApplicationError):
    pass
