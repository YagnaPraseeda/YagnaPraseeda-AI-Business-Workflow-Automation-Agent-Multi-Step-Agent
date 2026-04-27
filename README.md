# AI Business Workflow Automation Agent

A multi-step AI agent that interprets natural-language instructions and executes them through a dynamic tool-calling pipeline — powered by **Groq (Llama 3.3 70B)** and built with **FastAPI**.

Upload a file, type an instruction like *"Analyze this data and generate a report"*, and the agent figures out which tools to run, in what order, and shows you every step with timing and reasoning.

---

## Features

- **Natural-language task execution** — describe what you want; the agent decides the steps
- **ReAct-style agentic loop** — up to 20 tool-calling iterations with full message history
- **Step-by-step execution log** — tool name, status badge, duration, and AI reasoning per step
- **Four built-in tools** — file reader, CSV data analyzer, AI summarizer, report generator
- **Markdown report output** — copy to clipboard or download as `.md`
- **Auto-recovery** — handles Llama's legacy function-call format transparently
- **Interactive API docs** — Swagger UI at `/docs`, ReDoc at `/redoc`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.11+ |
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Data | Pandas |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Markdown | [marked.js](https://marked.js.org) |

---

## Project Structure

```
├── app/
│   ├── agent/
│   │   └── core.py          # ReAct agentic loop
│   ├── api/
│   │   └── routes.py        # FastAPI endpoints
│   ├── models/
│   │   └── schemas.py       # Pydantic request/response models
│   ├── tools/
│   │   ├── registry.py      # Tool registration decorator
│   │   ├── file_reader.py   # FileReaderTool
│   │   ├── data_analyzer.py # DataAnalyzerTool
│   │   ├── summarizer.py    # SummarizationTool
│   │   └── report_generator.py # ReportGeneratorTool
│   └── main.py              # FastAPI app entry point
├── static/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── uploads/                 # Uploaded files (git-ignored)
├── reports/                 # Generated reports (git-ignored)
├── .env.example
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/YagnaPraseeda/YagnaPraseeda-AI-Business-Workflow-Automation-Agent-Multi-Step-Agent.git
cd YagnaPraseeda-AI-Business-Workflow-Automation-Agent-Multi-Step-Agent
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and add your Groq API key (free at [console.groq.com](https://console.groq.com)):

```env
GROQ_API_KEY=your_groq_api_key_here
MODEL=llama-3.3-70b-versatile
MAX_TOKENS=4096
UPLOAD_DIR=uploads
REPORTS_DIR=reports
```

### 5. Run the server

```bash
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Usage

### Supported workflows

| Instruction | Tools called |
|---|---|
| "Summarize this file" | FileReaderTool → SummarizationTool |
| "Analyze this data" | FileReaderTool → DataAnalyzerTool → SummarizationTool |
| "Analyze and generate a report" | FileReaderTool → DataAnalyzerTool → SummarizationTool → ReportGeneratorTool |
| "Extract key risks from this document" | FileReaderTool → SummarizationTool |

### Supported file types

`csv` `txt` `md` `json` `log`

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `POST` | `/api/v1/run` | Run a workflow |
| `POST` | `/api/v1/upload` | Upload a file |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc |

**POST `/api/v1/run` — example request:**

```json
{
  "instruction": "Analyze the sales data and generate a detailed report",
  "file_path": "uploads/sales.csv"
}
```

**Response:**

```json
{
  "instruction": "...",
  "status": "success",
  "result": "## Sales Analysis Report\n...",
  "execution_log": [
    {
      "step_number": 1,
      "tool_name": "FileReaderTool",
      "input": { "file_path": "uploads/sales.csv" },
      "output": "...",
      "duration_ms": 12.4,
      "timestamp": "2025-01-01T12:00:00",
      "reasoning": "Loading the file first to access its contents.",
      "status": "completed"
    }
  ],
  "total_duration_ms": 4821.3
}
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
