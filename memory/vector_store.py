import faiss
import numpy as np
import os
import pickle
from core.logger import logger
from core.llm_bridge import llm_bridge

class VectorStore:
    def __init__(self, index_dir="memory/vector_index", dimension=None):
        self.index_dir = index_dir
        # Try to detect dimension from a test embedding
        if dimension is None:
            test_emb = llm_bridge.embed("test")
            self.dimension = len(test_emb) if test_emb else 768
        else:
            self.dimension = dimension
            
        self.index_path = os.path.join(index_dir, "lia.index")
        self.metadata_path = os.path.join(index_dir, "metadata.pkl")
        self.index = None
        self.metadata = []

        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir)

        self.load()

    def load(self):
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
                logger.info(f"Loaded existing index with {len(self.metadata)} items.")
            except Exception as e:
                logger.error(f"Failed to load index: {e}")
                self._create_new_index()
        else:
            self._create_new_index()

    def _create_new_index(self):
        logger.info("Creating new FAISS index.")
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []

    def save(self):
        try:
            faiss.write_index(self.index, self.index_path)
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
            logger.info("Vector store saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")

    def add(self, vectors, metadata_list):
        if len(vectors) == 0:
            return
        vectors = np.array(vectors).astype('float32')
        self.index.add(vectors)
        self.metadata.extend(metadata_list)
        self.save()

    def add_text(self, text, metadata):
        vector = llm_bridge.embed(text)
        if vector:
            self.add([vector], [metadata])

    def search_text(self, query_text, k=5):
        query_vector = llm_bridge.embed(query_text)
        if not query_vector:
            return []
        return self.search(query_vector, k)

    def search(self, query_vector, k=5):
        if self.index.ntotal == 0:
            return []
        
        query_vector = np.array([query_vector]).astype('float32')
        distances, indices = self.index.search(query_vector, k)
        
        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx != -1 and idx < len(self.metadata):
                results.append({
                    "metadata": self.metadata[idx],
                    "score": float(distances[0][i])
                })
        return results

# Singleton-like instance helper
vector_store = VectorStore()
