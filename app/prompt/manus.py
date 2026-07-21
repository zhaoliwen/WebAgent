import os
from pathlib import Path
from datetime import datetime

def _load_knowledge_base() -> str:
    """加载知识库文件内容"""
    knowledge_dir = Path(__file__).parent.parent.parent / "knowledge"
    knowledge_content = []

    if knowledge_dir.exists():
        for file_path in knowledge_dir.glob("*.txt"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        # 转义大括号，避免与 str.format() 冲突
                        content = content.replace("{", "{{").replace("}", "}}")
                        knowledge_content.append(f"\n--- {file_path.name} ---\n{content}")
            except Exception:
                pass

    if knowledge_content:
        return "\n\n=== 知识库参考 ===\n以下是常见场景的处理方法，请优先参考：" + "".join(knowledge_content) + "\n=== 知识库结束 ===\n"
    return ""

def _get_current_time() -> str:
    """获取当前系统时间"""
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[now.weekday()]
    return f"当前系统时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')} {weekday}"

# 加载知识库内容
_KNOWLEDGE_BASE = _load_knowledge_base()

SYSTEM_PROMPT = (
    "你是 OpenManus，一个全能的 AI 助手，旨在解决用户提出的任何任务。你拥有各种工具可以使用，能够高效地完成复杂的请求。无论是编程、信息检索、文件处理、网页浏览，还是人机交互（仅在极端情况下），你都能处理。"
    "\n\n{current_time}"
    "\n初始目录是：{directory}"
    "\n\n重要提示：对于需要实时信息的任务（如机票价格、当前天气、股票价格、新闻等），你必须使用浏览器工具访问实时网站。永远不要编造或猜测信息。始终使用工具获取准确、最新的数据。"
    f"{_KNOWLEDGE_BASE}"
    "\n\n请使用中文回复用户。"
)

NEXT_STEP_PROMPT = """
根据用户需求，主动选择最合适的工具或工具组合。对于复杂任务，你可以分解问题并逐步使用不同工具来解决。使用每个工具后，清楚地解释执行结果并建议下一步。

对于需要实时或当前信息的任务（机票价格、天气、新闻等），你必须使用浏览器工具搜索并从网站检索实际数据。不要提供编造的信息。

## 信息获取策略（重要）
- 当浏览器页面的交互元素列表中已经包含所需信息时（如航班、价格、商品列表等），直接整理这些信息并使用 terminate 返回给用户
- 不需要反复调用 extract_content 工具，如果元素列表中有信息就直接使用
- 获取到足够信息后尽快完成任务，不要过度操作
- extract_content 工具对动态加载页面效果有限，优先使用元素列表中的文本信息

## 任务完成原则（重要）
- 对于"查询"类任务（如查机票、查价格、查天气等），获取到信息后应该**立即调用 terminate 返回结果**
- 不要等待用户确认，不要反复询问"是否需要其他帮助"
- 如果用户没有明确说需要后续操作（如预订、购买等），只需要返回查询结果即可
- 完成任务时在 terminate 的 status 参数中包含整理好的信息

如果你想在任何时候停止交互，请使用 `terminate` 工具/函数调用。
"""
