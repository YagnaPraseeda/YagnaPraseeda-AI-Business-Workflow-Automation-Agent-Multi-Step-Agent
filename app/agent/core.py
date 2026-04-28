import json
import os
import re
import time
from datetime import datetime

from groq import BadRequestError, Groq, RateLimitError

from app.models.schemas import ExecutionStep
from app.tools import context as ctx
from app.tools.registry import registry

_MAX_RETRIES = 4
_RETRY_BASE_WAIT = 2.0  # seconds


def _groq_create_with_retry(client: Groq, **kwargs):
    """Call client.chat.completions.create with exponential backoff on rate limits."""
    for attempt in range(_MAX_RETRIES):
        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError as exc:
            if attempt == _MAX_RETRIES - 1:
                raise
            # Parse suggested wait from error message, default to exponential backoff
            body = getattr(exc, "body", {}) or {}
            msg = (body.get("error", {}).get("message", "") if isinstance(body, dict) else str(exc))
            m = re.search(r"try again in (\d+(?:\.\d+)?)(ms|s)", msg)
            if m:
                val, unit = float(m.group(1)), m.group(2)
                suggested = val / 1000 if unit == "ms" else val
            else:
                suggested = 0
            wait = max(suggested + 1, _RETRY_BASE_WAIT * (2 ** attempt))
            time.sleep(wait)


_SYSTEM_PROMPT = """\
You are an AI workflow automation agent. You receive natural-language instructions
and execute them step-by-step using the tools available to you.

HOW TOOLS SHARE DATA:
Tools communicate through a shared context — you do NOT pass file content between tools.
FileReaderTool loads the file and stores it. Every subsequent tool reads it automatically.

TOOLS:
- FileReaderTool(file_path)
    Load a file. Always call this FIRST. Call it EXACTLY ONCE. Its response tells you
    the file type and which tool to call next — follow that guidance.

- DataAnalyzerTool(query)
    Analyze the loaded file statistically. CSV FILES ONLY.
    NEVER call this on .txt, .md, .json, or .log files — it will fail.

- SummarizationTool(instruction)
    Summarize or extract insights from the loaded content.
    Do NOT pass a 'text' argument — it reads the file automatically.

- ReportGeneratorTool(title)
    Save a structured Markdown report. Call this LAST when a report is requested.
    Do NOT pass 'sections' — it compiles from context automatically.

WORKFLOW RULES — use ONLY the tools needed, each tool ONCE:
- Text/doc file (.txt .md .json .log):
    FileReaderTool → SummarizationTool [→ ReportGeneratorTool if report requested]
- CSV/data file (.csv):
    FileReaderTool → DataAnalyzerTool → SummarizationTool [→ ReportGeneratorTool if report requested]

STRICT RULES:
- Never call FileReaderTool more than once
- Never call DataAnalyzerTool on a non-CSV file
- Never pass raw file content as a tool argument — tools read from context
- Stop as soon as the task is complete; do not loop
"""

_MAX_ITERATIONS = 20


def _build_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in registry._tools.values()
    ]


def _parse_legacy_calls(text: str) -> list[dict]:
    """Parse Llama's legacy <function=Name>{args}</function> format (handles variants like Name": too)."""
    calls = []
    for i, m in enumerate(re.finditer(r'<function=(\w+)[^{]*(\{.*?\}).*?</function>', text, re.DOTALL)):
        try:
            args = json.loads(m.group(2))
        except json.JSONDecodeError:
            args = {}
        calls.append({"id": f"legacy_call_{i}", "name": m.group(1), "args": args})

    return calls


class WorkflowAgent:
    def __init__(self) -> None:
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])
        self.model_name = os.environ.get("MODEL", "llama-3.3-70b-versatile")

    def run(
        self, instruction: str, file_path: str | None = None
    ) -> tuple[str, list[ExecutionStep]]:
        ctx.reset()  # fresh context for every workflow run

        execution_log: list[ExecutionStep] = []
        step_counter = 0

        user_message = instruction
        if file_path:
            user_message += f"\n\nFile is available at: {file_path}"

        messages: list[dict] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        tools = _build_tools()

        for _ in range(_MAX_ITERATIONS):
            tool_invocations: list[tuple[str, str, dict]] = []
            reasoning: str | None = None

            try:
                response = _groq_create_with_retry(
                    self.client,
                    model=self.model_name,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
                message = response.choices[0].message
                reasoning = message.content.strip() if message.content else None

                assistant_entry: dict = {"role": "assistant", "content": message.content or ""}
                if message.tool_calls:
                    assistant_entry["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ]
                    for tc in message.tool_calls:
                        try:
                            args = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            args = {}
                        tool_invocations.append((tc.id, tc.function.name, args))

                messages.append(assistant_entry)

                if not message.tool_calls:
                    return message.content or "", execution_log

            except BadRequestError as exc:
                # Llama sometimes outputs <function=Name>{args}</function> as plain text.
                # Parse it and recover so the workflow continues.
                body = getattr(exc, "body", {}) or {}
                err = body.get("error", {}) if isinstance(body, dict) else {}
                if err.get("code") != "tool_use_failed":
                    raise
                failed_gen = err.get("failed_generation", "")
                parsed = _parse_legacy_calls(failed_gen)
                if not parsed:
                    raise
                fake_calls = [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {"name": c["name"], "arguments": json.dumps(c["args"])},
                    }
                    for c in parsed
                ]
                messages.append({"role": "assistant", "content": "", "tool_calls": fake_calls})
                tool_invocations = [(c["id"], c["name"], c["args"]) for c in parsed]

            for tool_id, name, args in tool_invocations:
                t0 = time.time()
                try:
                    result = registry.execute(name, **args)
                    result_str = str(result)
                    status = "completed"
                except Exception as tool_exc:
                    result_str = f"Tool error: {tool_exc}"
                    status = "error"
                duration_ms = round((time.time() - t0) * 1_000, 2)

                step_counter += 1
                execution_log.append(
                    ExecutionStep(
                        step_number=step_counter,
                        tool_name=name,
                        input=args,
                        output=result_str[:600],
                        duration_ms=duration_ms,
                        timestamp=datetime.now().isoformat(),
                        reasoning=reasoning,
                        status=status,
                    )
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result_str,
                })

        return "Workflow completed (max iterations reached).", execution_log
