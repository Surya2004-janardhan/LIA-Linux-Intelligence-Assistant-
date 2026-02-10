import asyncio
from litellm import completion, acompletion
from core.config import config
from core.memory_manager import central_memory

class LLMBridge:
    def __init__(self):
        self.provider = config.get('llm.provider', 'ollama')
        self.model = config.get('llm.model', 'llama3')
        self.base_url = config.get('llm.base_url', 'http://localhost:11434')

    def generate(self, messages, **kwargs):
        """
        Generates a response using litellm to support multiple backends.
        """
        model_name = self.model
    def generate(self, messages, **kwargs):
        """
        Generates a response using litellm to support multiple backends.
        """
        model_name = self.model
        if self.provider == "ollama":
            model_name = f"ollama/{self.model}"
        
        try:
            response = completion(
                model=model_name,
                messages=messages,
                api_base=self.base_url if self.provider == "ollama" else None,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error connecting to LLM ({self.provider}): {str(e)}"

    async def generate_async(self, messages, **kwargs):
        """Asynchronous generation for parallel agent tasks."""
        model_name = self.model
        if self.provider == "ollama":
            model_name = f"ollama/{self.model}"
        
        # Inject Central System Instructions
        system_instruction = central_memory.get_system_prompt()
        messages.insert(0, {"role": "system", "content": system_instruction})

        try:
            response = await acompletion(
                model=model_name,
                messages=messages,
                api_base=self.base_url if self.provider == "ollama" else None,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Async Error ({self.provider}): {str(e)}"

# Singleton instance
llm_bridge = LLMBridge()
