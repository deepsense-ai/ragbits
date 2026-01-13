import asyncio
from datetime import datetime

from ragbits.agents import Agent, AgentResult, PostProcessor
from ragbits.agents._main import AgentOptions, AgentRunContext
from ragbits.core.llms.litellm import LiteLLM


class MarkdownTemplateFormatter(PostProcessor):
    """
    Post-processor that formats output using a markdown template.

    This demonstrates structured output formatting with consistent templates.
    Use case: Converting raw output to a required format (markdown template, structured fields).
    """

    def __init__(self, template: str) -> None:
        """
        Initialize with markdown template.

        Args:
            template: Markdown template with {placeholders}
        """
        self.template = template

    async def process(
        self,
        result: AgentResult,
        agent: Agent,
        options: AgentOptions | None = None,
        context: AgentRunContext | None = None,
    ) -> AgentResult:
        """
        Format agent output using markdown template.

        Args:
            result: The agent result to process
            agent: The agent instance
            options: Optional agent options
            context: Optional agent run context

        Returns:
            Modified agent result with template-formatted content
        """
        content = result.content

        # Use datetime for proper timestamp formatting
        formatted_content = self.template.format(content=content, timestamp=datetime.now().isoformat())

        return AgentResult(
            content=formatted_content,
            metadata={
                **result.metadata,
                "output_format": "markdown",
                "template_applied": True,
            },
            tool_calls=result.tool_calls,
            history=result.history,
            usage=result.usage,
        )


async def main() -> None:
    """
    Demonstrate format conversion post-processors.
    """
    llm = LiteLLM("gpt-4o-mini")

    markdown_template = """
# Agent Response Report

**Generated at:** {timestamp}

## Content

{content}

---
*This response was automatically formatted by the output function.*
"""

    markdown_formatter = MarkdownTemplateFormatter(template=markdown_template)

    agent = Agent(
        llm=llm,
        prompt="You are a helpful assistant that provides structured information.",
        post_processors=[markdown_formatter],
    )

    result = await agent.run("Explain what neural networks are in simple terms.")

    print("Markdown Formatted Output:")
    print(result.content)
    print(f"\nMetadata: {result.metadata}")


if __name__ == "__main__":
    asyncio.run(main())
