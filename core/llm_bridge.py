"""
LIA Multi-Provider LLM Bridge

Supports:
- Ollama (local)
- OpenAI (GPT-4)
- Groq (Mixtral)
- Google Gemini (Gemini Pro)
- Anthropic (Claude 3)

Uses standard litellm library if available, with direct HTTP fallback for Ollama.
"""
import os
import json
import requests
from typing import List, Dict, Any, Optional
from core.config import config
from core.logger import logger

try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False


class LLMBridge:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.provider = config.get("llm.provider", "ollama").lower()
        self.model = config.get("llm.model", "llama3")
        self.base_url = config.get("llm.base_url", "http://localhost:11434")
        self.api_key = config.get("llm.api_key") or os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY")
        
        self._initialized = True
        logger.info(f"LLM Bridge initialized: {self.provider}/{self.model}")

    def generate(self, messages: List[Dict[str, str]], response_format: Optional[Dict] = None, 
                 temperature: float = 0.2) -> str:
        """
        Unified generation method. supports JSON mode for Ollama/OpenAI.
        """
        try:
            # 1. Native Ollama (Direct HTTP for speed/simplicity)
            if self.provider == "ollama":
                return self._generate_ollama(messages, response_format, temperature)
            
            # 2. Litellm (OpenAI, Groq, Gemini, Anthropic, etc.)
            if LITELLM_AVAILABLE:
                return self._generate_litellm(messages, response_format, temperature)
            
            return "Error: Provider requires 'litellm' package. Run: pip install litellm"
            
        except Exception as e:
            logger.error(f"LLM Generation Failed: {e}")
            return f"Error connecting to LLM: {str(e)}"

    def _generate_ollama(self, messages: List[Dict[str, str]], response_format: Optional[Dict], 
                         temperature: float) -> str:
        """Direct Ollama API call."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096
            }
        }
        
        if response_format and response_format.get("type") == "json_object":
            payload["format"] = "json"
        
        try:
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to Ollama. Is it running? (ollama serve)"
        except Exception as e:
            return f"Ollama Error: {str(e)}"

    def _generate_litellm(self, messages: List[Dict[str, str]], response_format: Optional[Dict], 
                          temperature: float) -> str:
        """Uses litellm to abstract all other providers."""
        # Map provider names to litellm format if needed
        model_name = self.model
        if self.provider == "openai" and not model_name.startswith("gpt"):
            model_name = f"gpt-3.5-turbo"
        elif self.provider == "anthropic" and not model_name.startswith("claude"):
            model_name = "claude-3-opus-20240229"
        elif self.provider == "groq":
            model_name = f"groq/{self.model}"
        elif self.provider == "gemini":
            model_name = "gemini/gemini-pro"
            
        kwargs = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
        }
        
        if self.api_key:
            kwargs["api_key"] = self.api_key
        
        if response_format and response_format.get("type") == "json_object":
            kwargs["response_format"] = response_format

        try:
            response = litellm.completion(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            return f"LLM Provider Error ({self.provider}): {str(e)}"

    def check_health(self) -> bool:
        """Verifies connection to the configured LLM."""
        try:
            if self.provider == "ollama":
                resp = requests.get(self.base_url, timeout=2)
                return resp.status_code == 200
            # For APIs, we assume 'true' if library loads, actual check is first call
            return True
        except:
            return False


# Singleton
llm_bridge = LLMBridge()
