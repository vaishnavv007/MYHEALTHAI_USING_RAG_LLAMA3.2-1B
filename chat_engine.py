from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain

# Step 1: Load Embeddings
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-large-en-v1.5")

# Step 2: Load Vector Store
vector_store = FAISS.load_local("last_index", embeddings, allow_dangerous_deserialization=True)
retriever = vector_store.as_retriever()

# Step 3: Load LLM
llm = OllamaLLM(model="llama3.2:1b", temperature=0.7)

# Step 4: Prompt
prompt = PromptTemplate.from_template("""
You are MYHALTHAI — a warm, friendly, and highly informed health assistant. You provide clear, human-friendly answers to questions related to diseases, medications, treatments, and diet, based on the context provided.

🧠 Guidelines:
- Respond in a helpful and professional tone.
- DO NOT mention page numbers, table names, sections, document titles, or years.
- DO NOT say things like "According to the document..." or "Based on the table above...".
- If the answer is not found in the context, respond with:
  "I'm sorry, I couldn't find enough information in the current knowledge. Please consult a healthcare professional."

📄 Context:
{context}

❓ Question:
{input}

💬 Answer as MYHALTHAI:
""")
stuff_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)
rag_chain = create_retrieval_chain(retriever=retriever, combine_docs_chain=stuff_chain)

def ask_bot(prompt):
    result = rag_chain.invoke({"input": prompt})
    return result['answer']
