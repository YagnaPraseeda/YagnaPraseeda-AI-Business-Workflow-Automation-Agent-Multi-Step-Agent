import json
import os
import re
import time
from datetime import datetime

from groq import BadRequestError, Groq

from app.models.schemas import ExecutionStep
from app.tools.registry import registry

_SYSTEM_PROMPT = """\
You are an AI workflow automation agent. You receive natural-language instructions
and execute them step-by-step using the tools available to you.

Available tools and when to use them:
- FileReaderTool: Load a file's contents. Always use this first when a file is referenced.
- DataAnalyzerTool: Run statistical analysis on CSV data (shape, types, statistics, correlations, trends). Use after FileReaderTool for any data/CSV analysis task.
- SummarizationTool: Summarize text or extract insights using AI. Use when the task asks for a summary, key points, or insights.
- ReportGeneratorTool: Compile all findings into a structured Markdown report. Use as the final step when the task asks for a report or document.

Workflow decision rules — use ONLY the tools needed:
- "Summarize this file"             → FileReaderTool → SummarizationTool
- "Analyze this data"               → FileReaderTool → DataAnalyzerTool → SummarizationTool
- "Analyze and generate a report"   → FileReaderTool → DataAnalyzerTool → SummarizationTool → ReportGeneratorTool
- "Extract key risks from document" → FileReaderTool → SummarizationTool

Call tools directly using the function-calling API. Do not describe tool calls in plain text.
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
    """Parse Llama's legacy <function=Name>{args}</function> format."""
    calls = []
    for i, m in enumerate(re.finditer(r'<function=(\w+)>(.*?)</function>', text, re.DOTALL)):
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
                response = self.client.chat.completions.create(
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
                # Llama sometimes outputs <function=Name>{args}</function> as plain text
                # instead of using the structured tool_calls API. Parse and recover.
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
