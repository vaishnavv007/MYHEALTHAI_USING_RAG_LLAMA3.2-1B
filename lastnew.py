
# its a working code
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain

# Step 1: Load BGE-large embeddings
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-large-en-v1.5")

# Step 2: Load FAISS index
vector_store = FAISS.load_local("last_index", embeddings, allow_dangerous_deserialization=True)
retriever = vector_store.as_retriever()

# Step 3: Load Ollama LLM
llm = OllamaLLM(model="llama3.2:1b")  # Or another model you've pulled locally

# Step 4: Create Stuff Documents Chain
prompt = PromptTemplate.from_template("""
Answer the question based only on the following context:

<context>
{context}
</context>

Question: {input}
""")

stuff_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)

# Step 5: Create Retrieval Chain
rag_chain = create_retrieval_chain(retriever=retriever, combine_docs_chain=stuff_chain)

# Step 6: Chat Loop
print("🤖 RAG Chatbot ready! Ask questions from your medical & diet PDFs (type 'exit' to quit):\n")
while True:
    question = input("❓ You: ")
    if question.strip().lower() == "exit":
        print("👋 Goodbye!")
        break
    result = rag_chain.invoke({"input": question})
    print("🤖 Answer:", result["answer"])
