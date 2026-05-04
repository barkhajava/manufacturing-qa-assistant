import logging
import os
from datetime import date

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.tools import list_lines, query_metrics, get_defect_trends

MODEL = "claude-sonnet-4-5"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("agent")

def _system_prompt() -> str:
    today = date.today().isoformat()
    return (
        f"You are a manufacturing quality assistant. Today's date is {today}. "
        "Use this to resolve relative terms like 'this week', 'last month', or 'last 7 days' "
        "into concrete YYYY-MM-DD date ranges before calling any tool. "
        "Answer questions about production line defects using only the data returned by your tools. "
        "If the tools return no relevant data, say you don't know — never fabricate numbers. "
        "Be concise and specific: include line IDs, defect rates, and dates when available."
    )

TOOLS = [list_lines, query_metrics, get_defect_trends]


def _build_executor() -> AgentExecutor:
    llm = ChatAnthropic(
        model=MODEL,
        api_key=os.environ["ANTHROPIC_API_KEY"],
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", _system_prompt()),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])
    agent = create_tool_calling_agent(llm, TOOLS, prompt)
    # verbose=True makes LangChain print every tool call + result to stdout
    return AgentExecutor(agent=agent, tools=TOOLS, verbose=True)


_executor = _build_executor()


def chat(question: str, history: list[dict]) -> str:
    """Run the agent with the given question and prior conversation history.

    history items are {"role": "user"|"assistant", "content": "..."}
    """
    log.info("Question: %s", question)

    lc_history = []
    for msg in history:
        if msg["role"] == "user":
            lc_history.append(HumanMessage(content=msg["content"]))
        else:
            lc_history.append(AIMessage(content=msg["content"]))

    try:
        result = _executor.invoke({"input": question, "chat_history": lc_history})
        output = result["output"]
        # Newer langchain-anthropic versions return a list of content blocks
        if isinstance(output, list):
            output = " ".join(block.get("text", "") for block in output if isinstance(block, dict))
        log.info("Answer: %s", output)
        return output
    except Exception as e:
        log.exception("Agent error")
        return f"Error: {e}"
