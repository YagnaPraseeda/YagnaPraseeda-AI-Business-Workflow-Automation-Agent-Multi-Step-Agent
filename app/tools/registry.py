from typing import Callable, Any
from dataclasses import dataclass


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    function: Callable


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, name: str, description: str, parameters: dict):
        def decorator(func: Callable):
            self._tools[name] = Tool(
                name=name,
                description=description,
                parameters=parameters,
                function=func,
            )
            return func

        return decorator

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def execute(self, name: str, **kwargs) -> Any:
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found in registry")
        return tool.function(**kwargs)

    def to_claude_tools(self) -> list[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())


registry = ToolRegistry()
