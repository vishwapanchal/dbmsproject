import os
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from src.config import Config

class VectorEngine:
    def __init__(self):
        # Create data directory if it doesn't exist
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR)

        print(f"🧠 Loading Embedding Model ({Config.EMBEDDING_MODEL})...")
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL)
        self.index = None
        self.metadata = []

    def build_index(self, db_rows):
        """Creates vectors from DB rows and saves them."""
        if not db_rows:
            print("⚠️ No data to index.")
            return

        print("⚙️  Vectorizing projects...")
        texts = []
        self.metadata = []

        for pid, title, synopsis in db_rows:
            clean_synopsis = synopsis if synopsis else ""
            full_text = f"{title}: {clean_synopsis}"
            
            texts.append(full_text)
            self.metadata.append({
                "id": pid, 
                "name": title, 
                "synopsis": clean_synopsis
            })

        # Generate Embeddings
        embeddings = self.model.encode(texts)
        embeddings = np.array(embeddings).astype('float32')
        
        # Build FAISS Index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

        # Save to disk
        self._save()

    def _save(self):
        """Internal method to save index and metadata."""
        print(f"💾 Saving index to {Config.DATA_DIR}...")
        faiss.write_index(self.index, Config.INDEX_PATH)
        with open(Config.METADATA_PATH, "wb") as f:
            pickle.dump(self.metadata, f)
        print("✅ Index saved successfully.")

    def load_index(self):
        """Loads the index from disk."""
        if os.path.exists(Config.INDEX_PATH) and os.path.exists(Config.METADATA_PATH):
            self.index = faiss.read_index(Config.INDEX_PATH)
            with open(Config.METADATA_PATH, "rb") as f:
                self.metadata = pickle.load(f)
            return True
        return False

    def search(self, title, synopsis, top_k=3):
        """Searches for similar projects."""
        if self.index is None:
            raise FileNotFoundError("Index not loaded. Run indexer first.")

        query_text = f"{title}: {synopsis}"
        query_vector = self.model.encode([query_text])
        query_vector = np.array(query_vector).astype('float32')

        distances, indices = self.index.search(query_vector, k=top_k)
        
        results = []
        for i in range(top_k):
            idx = indices[0][i]
            if idx != -1 and idx < len(self.metadata):
                match = self.metadata[idx].copy()
                
                # RAW DISTANCE (Lower is better)
                raw_score = float(distances[0][i])
                
                # CONVERTED SCORE (0 to 100%, Higher is better)
                # This is a simple estimation: 1.0 distance is "far", 0.0 is "exact copy"
                similarity_percent = max(0, (1.5 - raw_score) / 1.5 * 100)
                
                match['distance'] = raw_score
                match['similarity'] = round(similarity_percent, 2)
                
                results.append(match)
        
        return results