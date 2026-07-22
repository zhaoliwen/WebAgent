from app.tool.base import BaseTool
from app.tool.bash import Bash
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.create_chat_completion import CreateChatCompletion
from app.tool.planning import PlanningTool
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.terminate import Terminate
from app.tool.tool_collection import ToolCollection
from app.tool.web_search import WebSearch


def __getattr__(name: str):
    # 延迟加载重型工具，避免 import Manus 时拖入 crawl4ai/torch 等
    if name == "Crawl4aiTool":
        from app.tool.crawl4ai import Crawl4aiTool

        return Crawl4aiTool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseTool",
    "Bash",
    "BrowserUseTool",
    "Terminate",
    "StrReplaceEditor",
    "WebSearch",
    "ToolCollection",
    "CreateChatCompletion",
    "PlanningTool",
    "Crawl4aiTool",
]
