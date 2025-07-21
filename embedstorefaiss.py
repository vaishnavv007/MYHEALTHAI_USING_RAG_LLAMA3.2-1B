# ✅ Step 1: Install Required Libraries
# in colab
# pip install -U langchain langchain-community faiss-cpu sentence-transformers pypdf!

# ✅ Step 2: Imports
import os
from pypdf import PdfReader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from google.colab import files

# ✅ Step 3: Upload Multiple PDFs (Book1, Book2, Diet PDF)
print("📚 Upload your PDFs (e.g., two medicine books and one diet PDF)...")
uploaded = files.upload()  # Use Shift + Click to select multiple files

# ✅ Step 4: Extract and Combine All PDF Text
def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text

all_text = ""
for filename in uploaded.keys():
    print(f"📖 Extracting: {filename}")
    all_text += extract_text_from_pdf(filename) + "\n"

print("✅ All PDFs processed.")

# ✅ Step 5: Chunk the text for embedding
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_text(all_text)

# ✅ Step 6: Use BAAI/bge-large-en-v1.5 for embeddings
print("🔍 Generating embeddings with BGE-large...")
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-large-en-v1.5")

# ✅ Step 7: Create FAISS vector store
vector_store = FAISS.from_texts(chunks, embedding=embeddings)

# ✅ Step 8: Save FAISS Index
save_path = "faiss_index"
os.makedirs(save_path, exist_ok=True)
vector_store.save_local(save_path)

print(f"✅ FAISS index saved to '{save_path}/'")
