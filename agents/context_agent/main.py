from sentence_transformers import SentenceTransformer
import chromadb
from groq import Groq
import json
import os
from dotenv import load_dotenv 
load_dotenv()

# -------------------------------
# Step 0: Initialize Groq
# -------------------------------
client = Groq(api_key=os.getenv("GROQ_API_KEY")) # 🔴 PUT YOUR KEY HERE


# -------------------------------
# Step 1: Groq Extraction Function
# -------------------------------
def extract_from_groq(job_description):
    prompt = f"""
Extract structured data from this job description.

Return ONLY JSON:
{{
  "role": "...",
  "skills": [
    {{"name": "...", "importance": 0.0 to 1.0}}
  ]
}}

Job Description:
{job_description}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    content = response.choices[0].message.content

    # Clean JSON if wrapped in ```
    content = content.strip().replace("```json", "").replace("```", "")

    return json.loads(content)


# -------------------------------
# Step 2: Load embedding model
# -------------------------------
print("Loading model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded!")


# -------------------------------
# Step 3: Input Job Description
# -------------------------------
job_description = """
Looking for a backend developer with strong JavaScript, Node.js and MongoDB.
Experience with REST APIs required.
"""


# -------------------------------
# Step 4: Extract structured data (Groq)
# -------------------------------
data = extract_from_groq(job_description)

role = data["role"]
skills = data["skills"]

print("Extracted Data:", data)


# -------------------------------
# Step 5: Build embedding text (weighted)
# -------------------------------
text = role + " with " + " ".join([
    s["name"] for s in skills for _ in range(max(1, int(s["importance"] * 3)))
])

print("Embedding text:", text)


# -------------------------------
# Step 6: Create embedding
# -------------------------------
embedding = model.encode(text)

print("Embedding created!")


# -------------------------------
# Step 7: Store in ChromaDB
# -------------------------------
client_db = chromadb.Client()
collection = client_db.get_or_create_collection(name="jobs")

collection.add(
    documents=[text],
    embeddings=[embedding.tolist()],
    metadatas=[{
        "role": role,
        "skills": [s["name"] for s in skills]   # must be simple list ✅
    }],
    ids=["job_1"]
)

print("Stored in ChromaDB!")


# -------------------------------
# Step 8: Test query
# -------------------------------
results = collection.query(
    query_embeddings=[embedding.tolist()],
    n_results=1
)

print("Query Result:", results)