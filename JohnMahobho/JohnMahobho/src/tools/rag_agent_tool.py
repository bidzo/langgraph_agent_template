import uuid
from langchain_core.tools import tool
from sub_agents.rag_agent import rag_specialist_agent

@tool
async def search_zesa_records(query: str):
    """Search and analyze ZESA internal records."""
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    result = await rag_specialist_agent.ainvoke(
        {"query": query, "retrieved_docs": []},
        config=config
    )

    return result["summary"]