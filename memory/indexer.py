import os
from sentence_transformers import SentenceTransformer
from memory.vector_store import vector_store
from core.logger import logger
from core.config import config

class Indexer:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        logger.info(f"Initializing Indexer with model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.vector_store = vector_store

    def index_files(self, root_dir, extensions=None):
        """
        Walks through the directory and indexes file names and paths.
        """
        if extensions is None:
            extensions = ['.txt', '.pdf', '.docx', '.py', '.md', '.log', '.sh']

        logger.info(f"Starting file indexing in: {root_dir}")
        
        indexed_count = 0
        batch_texts = []
        batch_metadata = []

        for root, dirs, files in os.walk(root_dir):
            if ".venv" in root or ".git" in root or "__pycache__" in root:
                continue

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in extensions:
                    file_path = os.path.join(root, file)
                    # We index the file name and parent folder for semantic search
                    text_to_index = f"File: {file} in {os.path.basename(root)}"
                    
                    batch_texts.append(text_to_index)
                    batch_metadata.append({
                        "filename": file,
                        "path": file_path,
                        "type": "file"
                    })
                    indexed_count += 1

                    # Batch processing to save memory
                    if len(batch_texts) >= 100:
                        self._process_batch(batch_texts, batch_metadata)
                        batch_texts = []
                        batch_metadata = []

        # Final batch
        if batch_texts:
            self._process_batch(batch_texts, batch_metadata)

        logger.info(f"Indexing complete. Indexed {indexed_count} files.")
        return indexed_count

    def _process_batch(self, texts, metadata):
        logger.info(f"Processing batch of {len(texts)} items...")
        embeddings = self.model.encode(texts)
        self.vector_store.add(embeddings, metadata)

    def search(self, query, k=5):
        """
        Searches the index for the most relevant files/commands.
        """
        logger.info(f"Searching memory for: '{query}'")
        query_embedding = self.model.encode([query])[0]
        return self.vector_store.search(query_embedding, k=k)

# Singleton-like instance helper
indexer = Indexer()
