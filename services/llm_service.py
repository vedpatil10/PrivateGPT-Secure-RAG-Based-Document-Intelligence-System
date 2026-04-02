"""
LLM Service — swappable LLM providers (llama-cpp-python, Ollama).
Optimized for 8GB RAM CPU-only inference using GGUF quantized models.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Generator

from config.settings import get_settings

logger = logging.getLogger("privategpt.llm")


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def load(self):
        """Load/initialize the model."""
        pass

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> str:
        """Generate a complete response."""
        pass

    @abstractmethod
    def stream(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> Generator[str, None, None]:
        """Stream response tokens one at a time."""
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        pass


class LlamaCppProvider(BaseLLMProvider):
    """
    LLM provider using llama-cpp-python for GGUF model inference.
    Runs entirely on CPU, optimized for 8GB RAM systems.
    """

    def __init__(self):
        self._model = None
        settings = get_settings()
        self.model_path = settings.llm_model_path
        self.n_ctx = settings.llm_context_length
        self.n_threads = settings.llm_n_threads
        self.n_gpu_layers = settings.llm_n_gpu_layers

    def load(self):
        """Load the GGUF model."""
        from llama_cpp import Llama

        logger.info(f"Loading GGUF model: {self.model_path}")
        logger.info(f"Context: {self.n_ctx}, Threads: {self.n_threads}, GPU layers: {self.n_gpu_layers}")

        self._model = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_threads=self.n_threads,
            n_gpu_layers=self.n_gpu_layers,
            verbose=False,
        )

        logger.info("GGUF model loaded successfully")

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> str:
        """Generate a complete response."""
        if not self.is_loaded():
            self.load()

        response = self._model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.9,
            repeat_penalty=1.1,
            stop=["</s>", "\n\nHuman:", "\n\nUser:", "[/INST]"],
        )

        return response["choices"][0]["text"].strip()

    def stream(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> Generator[str, None, None]:
        """Stream response tokens."""
        if not self.is_loaded():
            self.load()

        stream = self._model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.9,
            repeat_penalty=1.1,
            stop=["</s>", "\n\nHuman:", "\n\nUser:", "[/INST]"],
            stream=True,
        )

        for chunk in stream:
            token = chunk["choices"][0]["text"]
            if token:
                yield token

    def is_loaded(self) -> bool:
        return self._model is not None


class OllamaProvider(BaseLLMProvider):
    """
    LLM provider using Ollama for model serving.
    Ollama manages model downloads and inference.
    """

    def __init__(self):
        self._loaded = False
        settings = get_settings()
        self.base_url = settings.ollama_base_url
        self.model_name = settings.ollama_model

    def load(self):
        """Verify Ollama connection and model availability."""
        import httpx

        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            models = response.json().get("models", [])
            model_names = [m["name"].split(":")[0] for m in models]

            if self.model_name not in model_names:
                logger.warning(
                    f"Model '{self.model_name}' not found in Ollama. "
                    f"Available: {model_names}. Pulling model..."
                )
                # Attempt to pull the model
                pull_resp = httpx.post(
                    f"{self.base_url}/api/pull",
                    json={"name": self.model_name},
                    timeout=600,
                )
                pull_resp.raise_for_status()

            self._loaded = True
            logger.info(f"Ollama connected. Model: {self.model_name}")

        except Exception as e:
            logger.error(f"Ollama connection failed: {e}")
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running: https://ollama.ai"
            )

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> str:
        """Generate using Ollama API."""
        if not self.is_loaded():
            self.load()

        import httpx

        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                },
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["response"].strip()

    def stream(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> Generator[str, None, None]:
        """Stream using Ollama API."""
        if not self.is_loaded():
            self.load()

        import httpx

        with httpx.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1,
                },
            },
            timeout=120,
        ) as response:
            import json
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    token = data.get("response", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break

    def is_loaded(self) -> bool:
        return self._loaded


# ── Provider Registry ────────────────────────────────────────────

_PROVIDERS = {
    "llama_cpp": LlamaCppProvider,
    "ollama": OllamaProvider,
}

_instance: Optional[BaseLLMProvider] = None


def get_llm_service() -> BaseLLMProvider:
    """Get or create the LLM provider based on settings."""
    global _instance
    if _instance is None:
        settings = get_settings()
        provider_class = _PROVIDERS.get(settings.llm_provider)
        if not provider_class:
            raise ValueError(
                f"Unknown LLM provider: {settings.llm_provider}. "
                f"Available: {list(_PROVIDERS.keys())}"
            )
        _instance = provider_class()
    return _instance


def swap_llm_provider(provider_name: str, **kwargs):
    """Hot-swap to a different LLM provider."""
    global _instance
    provider_class = _PROVIDERS.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")
    _instance = provider_class()
    logger.info(f"LLM provider swapped to: {provider_name}")
