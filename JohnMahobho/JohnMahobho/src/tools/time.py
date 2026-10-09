from langchain_core.tools import tool
from datetime import datetime, timezone

# ---- Async tool implementations ----
@tool
async def utc_now() -> str:
    """Return the current UTC timestamp in ISO format."""
    # Pure CPU, but async tool keeps the interface consistent.
    return datetime.now(tz=timezone.utc).isoformat()