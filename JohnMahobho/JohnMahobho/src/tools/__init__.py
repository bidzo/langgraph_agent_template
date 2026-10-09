from .calculator import calculator
from .time import utc_now
from .rag_agent_tool import search_zesa_records

# Tools master list
all_tools = [calculator, utc_now, search_zesa_records]