import pytest

from ragbits.core.tools import Tool


class MyMockTool(Tool):
    """Test tool"""

    def __init__(self):
        self.state = 10

    @staticmethod
    @Tool.define(name="add_two_numbers", description="Add two numbers")
    async def my_mock_tool(a: int, b: int) -> int:
        return a + b

    @staticmethod
    @Tool.define(name="subtract_two_numbers", description="Subtract two numbers async")
    async def subtract_two_numbers(a: int, b: int) -> int:
        return a - b

    @Tool.define(name="get_state", description="Get state")
    async def get_state(self) -> int:
        return self.state


def test_tool_registration():
    tool = MyMockTool()
    tools = tool.get_available_tools()

    assert len(tools) == 3
    assert "add_two_numbers" in tools
    assert "subtract_two_numbers" in tools
    assert "get_state" in tools


@pytest.mark.asyncio
async def test_tool_execution():
    tool = MyMockTool()
    tools = tool.get_available_tools()

    assert await tools["subtract_two_numbers"].func(1, 2) == -1


@pytest.mark.asyncio
async def test_tool_execution_instance_method():
    tool = MyMockTool()
    tools = tool.get_available_tools()

    assert await tools["get_state"].func() == 10


def test_registration_fails_on_not_async():
    with pytest.raises(ValueError):

        class NotValidTool(Tool):
            """Test tool"""

            x = 10

            @Tool.define(name="add_two_numbers", description="Add two numbers")
            def my_mock_tool(self) -> int:
                return self.x
