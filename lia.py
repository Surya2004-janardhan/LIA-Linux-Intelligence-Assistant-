from core.config import config
from core.llm_bridge import llm_bridge
from core.logger import logger
from memory.indexer import indexer
import sys

def main():
    logger.info("Initializing LIA...")
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "index":
            logger.info("Phase 2: Starting manual index...")
            count = indexer.index_files(".")
            print(f"✅ Indexed {count} files in the current directory.")
            return

        if cmd == "search":
            query = " ".join(sys.argv[2:])
            logger.info(f"Phase 2: Searching for '{query}'...")
            results = indexer.search(query)
            print("\n--- SEMANTIC SEARCH RESULTS ---")
            for res in results:
                print(f"Score: {res['score']:.4f} | Path: {res['metadata']['path']}")
            print("-------------------------------\n")
            return

    # Default logic (Phase 1)
    provider = config.get('llm.provider')
    logger.info(f"LLM Provider: {provider}")
    logger.info("LIA Ready. Use 'index' or 'search <query>' to test Phase 2.")
    
    print("\n--- LIA STATUS ---")
    print(f"Provider: {provider}")
    print(f"Model: {config.get('llm.model')}")
    print("Memory: Ready (Semantic Search Enabled)")
    print("------------------\n")

if __name__ == "__main__":
    main()
