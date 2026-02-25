import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# ----------------------------
# Load FAISS index from disk
# ----------------------------
def load_faiss_index_and_chunks():
    index = faiss.read_index("faiss.index")
    chunks = pickle.load(open("chunks.pkl", "rb"))
    return index, chunks

# ----------------------------
# Load stored chunks
# ----------------------------
def retrive_relavant_chunks(query: str):
    index, chunks = load_faiss_index_and_chunks()

    model = SentenceTransformer("all-mpnet-base-v2")

    query_vector = model.encode([query])

    # IMPORTANT: normalize if you used cosine similarity (IndexFlatIP)
    faiss.normalize_L2(query_vector)

    # Search
    D, I = index.search(np.array(query_vector), k=3)
    print("D = ",D)
    print("I = ", I)
    retrieved_chunks = []
    for i in range(len(I[0])):
        if D[0][i] > 0.35:
            retrieved_chunks.append(chunks[I[0][i]])
    if len(retrieved_chunks) == 0 :
        return "No relevant information found in the document."
    print("Retrieved Chunks:")
    h1 = 0
    for chunk in retrieved_chunks:
        print("chunk",str(h1)+" : "+ chunk)
        h1 += 1

    # Combine context
    context = "\n\n".join(retrieved_chunks)
    return context

# Gemini prompt
def gemini_generation(context: str, query: str):
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    prompt = f"""
    Answer the question using only the context below.
    If the answer is not in the context, say "Not found in document."

    Context:
    {context}

    Question:
    {query}
    """

    gemini = genai.GenerativeModel("gemini-2.5-flash")
    response = gemini.generate_content(prompt)

    print(response)
    return response

if __name__ == "__main__":
    query = "what is claim number."
    context = retrive_relavant_chunks(query)
    response = gemini_generation(context, query)
    print(response)
