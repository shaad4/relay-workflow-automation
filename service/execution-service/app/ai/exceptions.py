
class AIProviderError(Exception):
    """Base exception for AI provider failures."""


class AIAuthenticationError(AIProviderError):
    """Invalid or unauthorized provider credentials."""


class AIRateLimitError(AIProviderError):
    """Provider rate limit or quota exceeded."""


class AITimeoutError(AIProviderError):
    """AI provider request timed out."""


class AIServiceUnavailableError(AIProviderError):
    """AI provider is temporarily unavailable."""


class AIResponseError(AIProviderError):
    """AI provider returned an invalid or incomplete response."""
