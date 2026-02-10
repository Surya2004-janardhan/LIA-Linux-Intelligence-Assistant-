import faiss
import numpy as np
import os
import pickle
from core.logger import logger

class VectorStore:
    def __init__(self, index_dir="memory/vector_index", dimension=384):
        self.index_dir = index_dir
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
