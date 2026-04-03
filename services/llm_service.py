"""
Swappable LLM providers for llama.cpp, Ollama, and HuggingFace Transformers.
"""

import logging
from abc import ABC, abstractmethod
from threading import Thread
from typing import Generator, Optional

from config.settings import get_settings

logger = logging.getLogger("privategpt.llm")


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def load(self):
        """Load/initialize the model."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> str:
        """Generate a complete response."""

    @abstractmethod
    def stream(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> Generator[str, None, None]:
        """Stream response tokens one at a time."""

    @abstractmethod
    def is_loaded(self) -> bool:
        """Return whether the provider is initialized."""


class LlamaCppProvider(BaseLLMProvider):
    """GGUF inference through llama-cpp-python."""

    def __init__(self):
        self._model = None
        settings = get_settings()
        self.model_path = settings.llm_model_path
        self.n_ctx = settings.llm_context_length
        self.n_threads = settings.llm_n_threads
        self.n_gpu_layers = settings.llm_n_gpu_layers

    def load(self):
        from llama_cpp import Llama

        logger.info("Loading llama.cpp model from %s", self.model_path)
        self._model = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_threads=self.n_threads,
            n_gpu_layers=self.n_gpu_layers,
            verbose=False,
        )

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> str:
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
    """Ollama-backed inference."""

    def __init__(self):
        self._loaded = False
        settings = get_settings()
        self.base_url = settings.ollama_base_url
        self.model_name = settings.ollama_model

    def load(self):
        import httpx

        response = httpx.get(f"{self.base_url}/api/tags", timeout=10)
        response.raise_for_status()
        models = response.json().get("models", [])
        model_names = [m["name"].split(":")[0] for m in models]

        if self.model_name not in model_names:
            logger.info("Pulling missing Ollama model %s", self.model_name)
            pull_resp = httpx.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model_name},
                timeout=600,
            )
            pull_resp.raise_for_status()

        self._loaded = True

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> str:
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
        if not self.is_loaded():
            self.load()

        import httpx
        import json

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
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                token = data.get("response", "")
                if token:
                    yield token
                if data.get("done"):
                    break

    def is_loaded(self) -> bool:
        return self._loaded


class HuggingFaceProvider(BaseLLMProvider):
    """Transformers-based local inference with optional quantization."""

    def __init__(self):
        self._model = None
        self._tokenizer = None
        self._pipeline = None
        settings = get_settings()
        self.model_id = settings.hf_model_id
        self.auth_token = settings.hf_auth_token
        self.device_map = settings.hf_device_map
        self.load_in_4bit = settings.hf_load_in_4bit
        self.load_in_8bit = settings.hf_load_in_8bit
        self.trust_remote_code = settings.hf_trust_remote_code

    def load(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

        logger.info("Loading HuggingFace model %s", self.model_id)

        model_kwargs = {"device_map": self.device_map, "trust_remote_code": self.trust_remote_code}
        if self.load_in_4bit:
            model_kwargs["load_in_4bit"] = True
        elif self.load_in_8bit:
            model_kwargs["load_in_8bit"] = True

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_id,
            token=self.auth_token,
            trust_remote_code=self.trust_remote_code,
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            token=self.auth_token,
            **model_kwargs,
        )
        self._pipeline = pipeline(
            "text-generation",
            model=self._model,
            tokenizer=self._tokenizer,
        )

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> str:
        if not self.is_loaded():
            self.load()

        outputs = self._pipeline(
            prompt,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            top_p=0.9,
            return_full_text=False,
        )
        return outputs[0]["generated_text"].strip()

    def stream(self, prompt: str, max_tokens: int = 512, temperature: float = 0.1) -> Generator[str, None, None]:
        if not self.is_loaded():
            self.load()

        from transformers import TextIteratorStreamer

        streamer = TextIteratorStreamer(self._tokenizer, skip_prompt=True, skip_special_tokens=True)
        inputs = self._tokenizer(prompt, return_tensors="pt")
        inputs = {key: value.to(self._model.device) for key, value in inputs.items()}

        generation_kwargs = {
            **inputs,
            "streamer": streamer,
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "do_sample": temperature > 0,
            "top_p": 0.9,
        }

        worker = Thread(target=self._model.generate, kwargs=generation_kwargs, daemon=True)
        worker.start()

        for token in streamer:
            if token:
                yield token

    def is_loaded(self) -> bool:
        return self._pipeline is not None


_PROVIDERS = {
    "llama_cpp": LlamaCppProvider,
    "ollama": OllamaProvider,
    "huggingface": HuggingFaceProvider,
}

_instance: Optional[BaseLLMProvider] = None


def get_llm_service() -> BaseLLMProvider:
    """Get or create the configured LLM provider."""
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


def swap_llm_provider(provider_name: str, **_kwargs):
    """Hot-swap to a different LLM provider."""
    global _instance
    provider_class = _PROVIDERS.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")
    _instance = provider_class()
    logger.info("LLM provider swapped to %s", provider_name)
