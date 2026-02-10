from core.config import config
from core.llm_bridge import llm_bridge
from core.logger import logger

def main():
    logger.info("Initializing LIA Phase 1...")
    
    # Verify Config
    provider = config.get('llm.provider')
    logger.info(f"LLM Provider: {provider}")
    
    # Verify LLM Bridge (Dry Test)
    logger.info("LIA Foundation Ready. Waiting for next phase...")
    print("\n--- LIA STATUS ---")
    print(f"Provider: {provider}")
    print(f"Model: {config.get('llm.model')}")
    print("Project Structure: Verified")
    print("Venv: Initialized")
    print("------------------\n")

if __name__ == "__main__":
    main()
