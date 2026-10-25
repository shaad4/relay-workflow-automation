import os

from cryptography.fernet import Fernet, InvalidToken


class CredentialEncryption:
    def __init__(self):
        encryption_key = os.getenv("ACTION_CREDENTIAL_ENCRYPTION_KEY")

        if not encryption_key:
            raise RuntimeError("ACTION_CREDENTIAL_ENCRYPTION_KEY is not configured")

        try:
            self.cipher = Fernet(encryption_key.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise RuntimeError("Invalid credential encryption key") from exc

    def encrypt(self, credential: str) -> str:
        if not isinstance(credential, str) or not credential:
            raise ValueError("Credential cannot be empty")

        encrypted = self.cipher.encrypt(credential.encode("utf-8"))

        return encrypted.decode("utf-8")

    def decrypt(self, encrypted_credential: str) -> str:
        if not encrypted_credential:
            raise ValueError("Encrypted credential is required")

        try:
            decrypted = self.cipher.decrypt(encrypted_credential.encode("utf-8"))
        except (InvalidToken, ValueError) as exc:
            raise ValueError("Unable to decrypt credential") from exc

        return decrypted.decode("utf-8")
