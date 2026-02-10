from litellm import completion
from core.config import config

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

# Singleton instance
llm_bridge = LLMBridge()
