import asyncio
from litellm import completion, acompletion
from core.config import config
from core.logger import logger

class LLMBridge:
    def __init__(self):
        self.provider = config.get('llm.provider', 'ollama')
        self.model = config.get('llm.model', 'llama3')
        self.base_url = config.get('llm.base_url', 'http://localhost:11434')

    def _get_model_name(self):
        if self.provider == "ollama":
            return f"ollama/{self.model}"
        return self.model

    def generate(self, messages, **kwargs):
        """Synchronous LLM generation."""
        model_name = self._get_model_name()
        try:
            response = completion(
                model=model_name,
                messages=messages,
                api_base=self.base_url if self.provider == "ollama" else None,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed ({self.provider}): {e}")
            return f"Error connecting to LLM ({self.provider}): {str(e)}"

    async def generate_async(self, messages, **kwargs):
        """Asynchronous LLM generation for parallel agent tasks."""
        model_name = self._get_model_name()
        try:
            response = await acompletion(
                model=model_name,
                messages=messages,
                api_base=self.base_url if self.provider == "ollama" else None,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Async LLM call failed ({self.provider}): {e}")
            return f"Async Error ({self.provider}): {str(e)}"

# Singleton instance
llm_bridge = LLMBridge()
