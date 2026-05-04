# Architecture

A plain-English walkthrough of how the Manufacturing QA Assistant is structured and how a request flows through it.

---

## Module Overview

```
app/
├── main.py    — FastAPI app: HTTP routes, request/response models
├── agent.py   — LangChain agent: prompt, memory, LLM wiring
├── tools.py   — Three @tool functions the agent can call
└── db.py      — SQLite helpers (get_connection, fetch_all, fetch_one)

app/static/
└── index.html — Single-page chat UI (vanilla JS, no framework)

data/
└── manufacturing.db — SQLite database (production_lines + daily_metrics)
```

---

## Component Diagram

Shows how the modules depend on each other and what external services they talk to.

```mermaid
graph TD
    Browser["🌐 Browser\nindex.html\n(vanilla JS)"]
    FastAPI["⚡ FastAPI\nmain.py\nPOST /chat"]
    Agent["🤖 Agent\nagent.py\nAgentExecutor"]
    Tools["🔧 Tools\ntools.py\nlist_lines · query_metrics\nget_defect_trends"]
    DB["🗄️ DB Layer\ndb.py\nfetch_all · fetch_one"]
    SQLite[("SQLite\nmanufacturing.db")]
    Claude["☁️ Anthropic API\nclaude-sonnet-4-5"]

    Browser -- "POST /chat\n{question, history}" --> FastAPI
    FastAPI -- "chat(question, history)" --> Agent
    Agent -- "tool calls" --> Tools
    Tools -- "SQL queries" --> DB
    DB -- "rows" --> Tools
    Tools -- "structured data" --> Agent
    Agent -- "prompt + history\n+ tool results" --> Claude
    Claude -- "answer text" --> Agent
    Agent -- "answer" --> FastAPI
    FastAPI -- "{answer}" --> Browser
```

---

## Request Flow (Sequence Diagram)

Traces a single user message from the browser through every layer and back.

```mermaid
sequenceDiagram
    actor User
    participant UI as index.html<br/>(Browser)
    participant API as main.py<br/>(FastAPI)
    participant Ag as agent.py<br/>(AgentExecutor)
    participant LLM as Anthropic API<br/>(Claude)
    participant T as tools.py
    participant DB as db.py + SQLite

    User->>UI: Types question, hits Send
    UI->>UI: Appends {role:user} to local history[]
    UI->>API: POST /chat<br/>{question, history (all prior turns)}

    API->>Ag: chat(question, history)
    Ag->>Ag: Convert history dicts<br/>→ HumanMessage / AIMessage

    loop Agent reasoning loop (may repeat for each tool call)
        Ag->>LLM: system prompt + chat_history<br/>+ current question + scratchpad
        LLM-->>Ag: Decide: call a tool OR produce final answer

        alt LLM calls a tool
            Ag->>T: list_lines() OR<br/>query_metrics(line, start, end) OR<br/>get_defect_trends(line, weeks)
            T->>DB: SQL query via fetch_all / fetch_one
            DB-->>T: Row dicts from SQLite
            T-->>Ag: Structured result (list / dict)
            Note over Ag: Result added to scratchpad,<br/>loop continues
        else LLM produces final answer
            LLM-->>Ag: Answer text
        end
    end

    Ag-->>API: answer string
    API-->>UI: {answer: "..."}
    UI->>UI: Renders assistant bubble<br/>Appends {role:assistant} to history[]
    UI-->>User: Sees the answer
```

---

## Memory Model

The agent itself is **stateless** — `AgentExecutor` stores nothing between calls.

Session memory is managed entirely by the browser:

```
history[] lives in JS (index.html)
│
├── On every send:   history is sent to the server as part of the request body
├── On every reply:  the assistant answer is pushed into history[]
└── On "Back" btn:   history.length = 0  →  session is reset
```

The server converts that list into LangChain `HumanMessage` / `AIMessage` objects and injects them into the prompt via `MessagesPlaceholder("chat_history")`. This gives the LLM full context of the conversation without any server-side storage.

---

## Database Schema

```
production_lines
  line_id       TEXT  PRIMARY KEY   e.g. "A"
  description   TEXT

daily_metrics
  id            INTEGER PRIMARY KEY
  line_id       TEXT    REFERENCES production_lines
  date          TEXT    YYYY-MM-DD
  units_produced INTEGER
  defect_count  INTEGER
  top_defect_type TEXT
```

---

## Tools the Agent Can Use

| Tool | When the agent uses it | Returns |
|---|---|---|
| `list_lines()` | User asks which lines exist | List of `{line_id, description}` |
| `query_metrics(line, start, end)` | User asks about a specific line + date range | `{defect_count, defect_rate, top_defect_type}` |
| `get_defect_trends(line, weeks)` | User asks for trends / week-over-week | List of `{week, defect_rate}` |

The LLM resolves relative dates ("last month", "this week") into concrete `YYYY-MM-DD` ranges before calling any tool — this is enforced in the system prompt.
