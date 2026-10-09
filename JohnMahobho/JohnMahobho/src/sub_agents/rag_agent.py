
import time  # FIXED: Correct import for time.sleep
import pandas as pd
import operator
from typing import TypedDict, Annotated, List
from pathlib import Path

# Google & LangChain Imports
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langchain.chat_models import init_chat_model

from dotenv import load_dotenv

# data location
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "rag_files"

# ---- Init ----
load_dotenv()
# vertexai.init(project=os.getenv("GOOGLE_CLOUD_PROJECT"), location="us-central1")

# --- 1. INCREMENTAL VECTOR STORE MANAGER ---
class ZESAIncrementalStore:
    def __init__(self):
        self.persist_dir = "./zesa_gemini_db"

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            task_type="retrieval_document"
        )
        self.vectorstore = Chroma(
            persist_directory=self.persist_dir,
            embedding_function=self.embeddings
        )

    def update_data(self):
        """Loads CSVs and only adds records that aren't already in Chroma."""
        datasets = {
            "work": str(DATA_DIR / "daily_work_update.csv"),
            "audit": str(DATA_DIR / "meter-audits.csv"),
            "bypass": str(DATA_DIR / "zero-to-low-purchase.csv"),
            "cms": str(DATA_DIR / "cms.csv"),
        }

        #  please check out langchain document loaders to encapsulate creating of langgraph documents

        # OPTIMIZATION: Get all existing IDs once to avoid 10,000+ DB calls
        print("--- Checking existing records ---")
        existing_data = self.vectorstore.get()
        existing_ids = set()
        if existing_data and 'metadatas' in existing_data:
            existing_ids = {m.get('id') for m in existing_data['metadatas'] if m}

        new_documents = []

        # 1. Process Artisan Work
        df_work = pd.read_csv(datasets["work"])
        for _, row in df_work.iterrows():
            uid = str(row['ec5_uuid'])
            if uid not in existing_ids:
                text = f"WORK UPDATE: {row['3_Work_Done']} by {row['created_by']}. {row['6_Comments']}"
                new_documents.append(Document(page_content=text, metadata={"source": "daily_work", "id": uid}))
                existing_ids.add(uid)

        # 2. Process Meter Audits
        df_audit = pd.read_csv(datasets["audit"])
        for _, row in df_audit.iterrows():
            uid = str(row['ec5_uuid'])
            if uid not in existing_ids:
                text = f"AUDIT: Meter {row['3_Meter_Number']}. Anomalies: {row['6_Anomalies_Found_On']}. Comment: {row['12_Comments']}"
                new_documents.append(Document(page_content=text, metadata={"source": "meter_audits", "id": uid}))
                existing_ids.add(uid)

        # 3. Process Bypass Alerts
        df_bypass = pd.read_csv(datasets["bypass"])
        for _, row in df_bypass.iterrows():
            meter_id = str(row['Meter_number'])
            if meter_id not in existing_ids:
                text = f"BYPASS ALERT: Meter {meter_id}. Deviation: {row['Percentage_deviation']}%. Days: {row['Days_since_last_purchase']}"
                new_documents.append(Document(page_content=text, metadata={"source": "bypass_alerts", "id": meter_id}))
                existing_ids.add(meter_id)

        # --- BATCHED UPLOAD ---
        if new_documents:
            print(f"--- Adding {len(new_documents)} new records in batches ---")
            batch_size = 20
            for i in range(0, len(new_documents), batch_size):
                batch = new_documents[i : i + batch_size]
                try:
                    self.vectorstore.add_documents(batch)
                    print(f"Progress: {i + len(batch)} / {len(new_documents)}")
                    time.sleep(6) # Now works because of 'import time'
                except Exception as e:
                    print(f"Failed at batch starting at {i}: {e}")
                    break
        else:
            print("--- Database is up to date ---")

# Initialize and Update
zesa_manager = ZESAIncrementalStore()
zesa_manager.update_data()

# --- 2. AGENT STATE ---
class RAGState(TypedDict):
    query: str
    retrieved_docs: Annotated[list, operator.add]
    summary: str
    risk_level: str
    supervisor_approved: bool

# --- 3. NODES ---
async def retrieve_node(state: RAGState):
    docs =  await zesa_manager.vectorstore.asimilarity_search(state["query"], k=8)
    formatted = [f"[{d.metadata['source'].upper()}]: {d.page_content}" for d in docs]
    return {"retrieved_docs": formatted}

async def analyze_node(state: RAGState):
    # Using a standard stable model name
    llm = init_chat_model("google_genai:gemini-2.5-flash-lite")

    context = "\n".join(state["retrieved_docs"])

    prompt = f"Analyze these ZESA records for the query: {state['query']}\n\nRECORDS:\n{context}\n\nCategorize risk as HIGH or LOW."
    response = await llm.ainvoke(prompt)

    risk = "HIGH" if "HIGH" in response.content.upper() else "LOW"
    return {"summary": response.content, "risk_level": risk}

# --- 4. GRAPH CONSTRUCTION ---
def route_risk(state: RAGState):
    return "human_review" if state["risk_level"] == "HIGH" else END

workflow = StateGraph(RAGState)
workflow.add_node("retriever", retrieve_node)
workflow.add_node("analyzer", analyze_node)
workflow.add_node("human_review", lambda x: x)

workflow.add_edge(START, "retriever")
workflow.add_edge("retriever", "analyzer")
workflow.add_conditional_edges("analyzer", route_risk, {"human_review": "human_review", END: END})
workflow.add_edge("human_review", END)

checkpointer = MemorySaver()
rag_specialist_agent = workflow.compile(checkpointer=checkpointer, interrupt_before=["human_review"])

# comment me out me im here to test the graph
# png_data = rag_specialist_agent.get_graph().draw_mermaid_png()
#
# with open("graph_output.png", "wb") as f:
#     f.write(png_data)
#
# print("Graph saved as graph_output.png")