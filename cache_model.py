"""
cache_model.py  — NEW FILE

Run this ONCE on your machine to download and cache the sentence-transformers model.
After this runs, the pipeline uses the cached model with TRANSFORMERS_OFFLINE=1.

Usage:
    python cache_model.py
"""
print("Downloading sentence-transformers model (all-MiniLM-L6-v2)...")
print("This runs once — subsequent pipeline runs use the local cache.")
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
test  = model.encode(["hello world"])
print(f"Model cached successfully. Embedding dim: {len(test[0])}")
print("You can now run the pipeline fully offline.")