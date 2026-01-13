"""
Output Function Use Case: Routing to Downstream Agent

This example demonstrates how PostProcessors can route agent output to downstream agents
for additional processing, such as summarization and formatting.

Use case: Routing or handing off results to other agents for post-processing as the final
step before returning the response.
"""

import asyncio

from ragbits.agents import Agent, AgentOptions, AgentResult, PostProcessor
from ragbits.agents._main import AgentRunContext
from ragbits.core.llms.litellm import LiteLLM


class SummarizerPostProcessor(PostProcessor):
    """
    Post-processor that routes output to a downstream summarization agent.

    This demonstrates the "send summary to agent B" use case - routing output
    to a specialized agent for additional processing.
    Use case: Routing results to downstream agents for post-processing.
    """

    def __init__(self, summarizer_agent: Agent) -> None:
        """
        Initialize with summarizer agent.

        Args:
            summarizer_agent: Agent that will summarize and format the content
        """
        self.summarizer_agent = summarizer_agent

    async def process(
        self,
        result: AgentResult,
        agent: Agent,
        options: AgentOptions | None = None,
        context: AgentRunContext | None = None,
    ) -> AgentResult:
        """
        Route output to summarizer agent for processing.

        Args:
            result: The agent result to process
            agent: The agent instance
            options: Optional agent options
            context: Optional agent run context

        Returns:
            Modified agent result with summarized and formatted content
        """
        content = result.content

        # Create instruction for summarizer agent
        summarizer_instruction = (
            f"Please create a concise summary of the following content. "
            f"Start and end the summary with [SUMMARY] indicator\n\n"
            f"Content to summarize:\n---\n{content}\n---"
        )

        # Route to summarizer agent
        summarized_result = await self.summarizer_agent.run(summarizer_instruction, options=options, context=context)

        return AgentResult(
            content=summarized_result.content,
            metadata={
                **result.metadata,
                "post_processing": {
                    "routed_to_agent": self.summarizer_agent.name,
                    "original_content": content,
                    "original_length": len(content),
                    "summarized_length": len(summarized_result.content),
                    "compression_ratio": round(len(summarized_result.content) / len(content), 2),
                },
            },
            tool_calls=result.tool_calls,
            history=result.history,
            usage=result.usage,
        )


async def main() -> None:
    """Demonstrate routing agent output to downstream agents for post-processing."""
    llm = LiteLLM("gpt-4o-mini")

    # Create the main content agent
    main_agent = Agent(
        name="content_agent",
        llm=llm,
        prompt="You are a helpful assistant that provides detailed explanations.",
    )

    # Create the summarizer agent with specific instructions
    summarizer_agent = Agent(
        name="summarizer_agent",
        llm=llm,
        prompt=(
            "You are an expert summarizer. Your task is to create concise summaries "
            "that preserve key information while being much shorter than the original. "
            "Always use markdown bold (**text**) to highlight the most important points."
        ),
        default_options=AgentOptions(max_total_tokens=2000),
    )

    # Create the post-processor
    summarizer_processor = SummarizerPostProcessor(summarizer_agent)

    # Create agent with post-processor
    main_agent_with_processor = Agent(
        name="content_agent_with_processor",
        llm=llm,
        prompt="You are a helpful assistant that provides detailed explanations.",
        post_processors=[summarizer_processor],
    )

    # Run the main agent with post-processing
    result = await main_agent_with_processor.run(
        "Explain the concept of machine learning in detail, including supervised learning, "
        "unsupervised learning, and reinforcement learning. Describe each type with examples "
        "and their real-world applications.",
    )

    print(f"Final output:\n {result.content}")
    print(f"Original output:\n {result.metadata['post_processing']['original_content']}")


if __name__ == "__main__":
    asyncio.run(main())
