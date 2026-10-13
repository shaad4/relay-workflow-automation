import os

from cryptography.fernet import Fernet, InvalidToken


class CredentialEncryption:

    def __init__(self):
        encryption_key = os.getenv(
            "AI_CREDENTIAL_ENCRYPTION_KEY"
        )

        if not encryption_key:
            raise RuntimeError(
                "AI_CREDENTIAL_ENCRYPTION_KEY is not configured"
            )

        try:
            self.cipher = Fernet(
                encryption_key.encode("utf-8")
            )
        except (ValueError, TypeError) as exc:
            raise RuntimeError(
                "Invalid AI credential encryption key"
            ) from exc

    def encrypt(self, api_key: str) -> str:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("API key cannot be empty")

        encrypted = self.cipher.encrypt(
            api_key.encode("utf-8")
        )

        return encrypted.decode("utf-8")

    def decrypt(self, encrypted_api_key: str) -> str:
        if not isinstance(encrypted_api_key, str) or not encrypted_api_key:
            raise ValueError("Encrypted API key is required")

        try:
            decrypted = self.cipher.decrypt(
                encrypted_api_key.encode("utf-8")
            )
        except (InvalidToken, ValueError) as exc:
            raise ValueError(
                "Unable to decrypt AI provider credentials"
            ) from exc

        return decrypted.decode("utf-8")
