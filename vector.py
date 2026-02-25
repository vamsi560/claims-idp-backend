from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Load PDF
reader = PdfReader(r"C:\practice\Files\uploaded_files\Demand Latter002.pdf")
text = "\n".join([page.extract_text() for page in reader.pages])

# Chunk
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
chunks = splitter.split_text(text)

# Embeddings
model = SentenceTransformer("all-mpnet-base-v2")
embeddings = model.encode(chunks)

# Normalize for cosine similarity
faiss.normalize_L2(embeddings)

dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(np.array(embeddings))
print(f"Indexed {index.ntotal} chunks.")
faiss.write_index(index, "faiss.index")
import pickle
pickle.dump(chunks, open("chunks.pkl", "wb"))

