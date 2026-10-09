
"""Minimal LangChain agent graph for deployment (async/await version)."""
from __future__ import annotations
import os
import vertexai
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

#Laod tools
from tools import all_tools

# ---- Init (no blocking network calls here, but keep order) ----
vertexai.init(project="gen-lang-client-0297089465", location="us-central1")

load_dotenv()
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")  # kept as you had it

# If init_chat_model performs sync IO during model setup, we can't make it
# truly async unless you use an async-capable SDK/API. This is the typical limitation.
llm =  init_chat_model("google_genai:gemini-2.5-flash-lite")

# ---- Build the agent graph ----
# create_agent is typically synchronous. If it does heavy IO, you'd need an
# async variant; otherwise there’s nothing to await.
graph = create_agent(
    model=llm,
    tools=all_tools,
    system_prompt=(
        "You are a concise assistant named LCA (AI) John Mahobho. "
        "Developed for ZESA Holdings Loss Control"
        "Use tools when they add factual precision, then return a direct answer."
    ),
    name="agent",
)
