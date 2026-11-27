"""Chat tool definitions and their handlers stay in sync."""

import pytest

from app.ai import tools
from app.ai.tools import TOOLS, ToolError, run_tool


def test_every_declared_tool_has_a_handler() -> None:
    assert {t["name"] for t in TOOLS} == set(tools._HANDLERS)


def test_unknown_tool_is_rejected() -> None:
    with pytest.raises(ToolError, match="Unknown tool"):
        run_tool("delete_everything", {}, facts=None)  # type: ignore[arg-type]
