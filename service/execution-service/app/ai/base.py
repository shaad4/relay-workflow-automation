from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class AIProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        api_key: str,
        model: str,
        instructions: str,
        prompt: str,
    ) -> AIResponse:
        """Generate a response using an LLM provider."""
        raise NotImplementedError
