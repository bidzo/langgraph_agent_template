"""LangChain agent graph using official MultiServerMCPClient and LangGraph StateGraph."""
from __future__ import annotations
import os
import sys
import asyncio
import vertexai
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient

# LangGraph imports
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

# Load core tools
from tools import all_tools

# ---- Init ----
vertexai.init(project="gen-lang-client-0297089465", location="us-central1")
load_dotenv()

llm = init_chat_model("google_genai:gemini-2.5-flash-lite")


def create_agent_graph(tools, system_prompt: str):
    """Builds and compiles the agent workflow graph."""

    # 1. Define the system node / LLM call
    def call_model(state: MessagesState):
        messages = [{"role": "system", "content": system_prompt}] + state["messages"]
        response = llm.bind_tools(tools).invoke(messages)
        return {"messages": [response]}

    # 2. Define the tool execution node
    tool_node = ToolNode(tools)

    # 3. Define conditional routing logic
    def should_continue(state: MessagesState):
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        return END

    # 4. Construct the State Graph
    workflow = StateGraph(MessagesState)

    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    # Add edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    workflow.add_edge("tools", "agent")

    # 5. Compile the workflow
    return workflow.compile()


async def main():
    # Configure all your servers in one unified dictionary structure
    mcp_config = {
        "epicollect5_server": {
            "transport": "stdio",
            "command": sys.executable,
            "env": {
                **os.environ,
                "EPICOLLECT_CLIENT_ID": os.getenv("EPICOLLECT_CLIENT_ID"),
                "EPICOLLECT_CLIENT_SECRET": os.getenv("EPICOLLECT_CLIENT_SECRET"),
            }
        }
    }

    # Initialize the client with your configuration map
    async with MultiServerMCPClient(mcp_config) as client:
        # Pull all converted tools from all connected servers simultaneously
        mcp_tools = await client.get_tools()
        print(f"Successfully connected to servers and loaded {len(mcp_tools)} tools.")

        # Merge with local tools
        combined_tools = all_tools + mcp_tools

        system_prompt = (
            "You are a concise assistant named LCA (AI) John Mahobho. "
            "Developed for ZESA Holdings Loss Control. "
            "Use tools when they add factual precision, then return a direct answer."
        )

        # ---- Build and Compile the Workflow Graph ----
        agent_graph = create_agent_graph(combined_tools, system_prompt)
        print("Agent workflow graph successfully compiled.")

        # ---- Example: Invoking the graph directly ----
        example_input = {
            "messages": [{"role": "user", "content": "Run a loss control check on active epicollect reports."}]}

        async for chunk in agent_graph.astream(example_input, stream_mode="values"):
            latest_message = chunk["messages"][-1]
            latest_message.pretty_print()

        # ---- Note on Parent Agent Invocation ----
        # If another agent wants to invoke this graph as a tool, you can convert it using:
        # from langchain.tools import Tool
        #
        # agent_tool = Tool(
        #     name="LCA_John_Mahobho_Agent",
        #     description="Invoke this agent to handle ZESA Holdings Loss Control operations.",
        #     func=agent_graph.invoke,
        #     coroutine=agent_graph.ainvoke
        # )


if __name__ == "__main__":
    asyncio.run(main())