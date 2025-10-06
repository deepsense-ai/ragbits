"""
Todo: move somewhere else
Example usage of the MemoryTool with a regular Agent.

This example demonstrates how to add long-term memory capabilities
to any existing agent using the memory tool.
"""

import asyncio

from pydantic import BaseModel

from ragbits.agents import Agent
from ragbits.agents.tools.memory import LongTermMemory, create_memory_tools
from ragbits.core.embeddings import LiteLLMEmbedder
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore


class ConversationInput(BaseModel):
    """Input model for conversation prompts."""

    message: str


class ConversationPrompt(Prompt[ConversationInput, str]):
    """Prompt for conversation with memory capabilities."""

    system_prompt = """
    You are a helpful assistant with long-term memory. You can remember information
    from previous conversations and use it to provide more personalized responses.

    You have access to memory tools that allow you to:
    - Store important facts from conversations
    - Retrieve relevant memories based on queries

    Store all information about the user that might be useful in future conversations.
    Always start with retrieving memories (implicit) to provide more relevant and personalized experience.
    """

    user_prompt = """
    Message: {{ message }}
    """


async def main() -> None:
    """Demonstrate the memory tool functionality with comparison between agents with and without memory."""
    # Initialize components
    embedder = LiteLLMEmbedder(
        model_name="text-embedding-3-small",
    )

    # Create shared LLM instance (we'll create new agent instances for each conversation)
    llm = LiteLLM(
        model_name="gpt-4o-mini",
    )

    # Create shared vector store (persistent memory storage)
    shared_vector_store = InMemoryVectorStore(embedder=embedder)

    # Test conversations
    conversations: list[dict[str, str | ConversationInput]] = [
        {
            "title": "1. First conversation - storing information:",
            "input": ConversationInput(
                message="I love hiking in the mountains. I'm planning a trip to Rome next month."
            ),
        },
        {
            "title": "2. Second conversation - retrieving context:",
            "input": ConversationInput(message="What outdoor activities would you recommend for my trip?"),
        },
        {
            "title": "3. Different user (different memory key):",
            "input": ConversationInput(message="Hi! I love cooking Asian food."),
        },
        {
            "title": "4. 2nd user asking about travel (should not know 1st user's info):",
            "input": ConversationInput(message="What do you know about my travel interests?"),
        },
    ]

    # Run conversations with both agents
    for i, conv in enumerate(conversations, 1):
        print(f"{conv['title']}")
        print("=" * 60)

        long_term_memory = LongTermMemory(embedder=embedder, vector_store=shared_vector_store)

        # First two conversations use user_123, last two use user_456
        USER_123_THRESHOLD = 2
        user_id = "user_123" if i <= USER_123_THRESHOLD else "user_456"

        # Create fresh agent instances for each conversation
        # (otherwise the agent remembers the previous conversation even without memory)
        agent_with_memory = Agent(
            llm=llm, prompt=ConversationPrompt, tools=create_memory_tools(long_term_memory, user_id), keep_history=False
        )

        agent_without_memory = Agent(llm=llm, prompt=ConversationPrompt, tools=[], keep_history=False)

        # Agent WITH memory
        print("Agent WITH Memory:")
        input_data = conv["input"]
        if not isinstance(input_data, ConversationInput):
            raise TypeError("Expected ConversationInput")
        response_with = await agent_with_memory.run(input_data)
        print(f"Response: {response_with.content}\n")

        # Agent WITHOUT memory
        print("Agent WITHOUT Memory:")
        response_without = await agent_without_memory.run(input_data)
        print(f"Response: {response_without.content}\n")

        print("-" * 60)
        print()

    # Manual memory operations demonstration (internal methods only)
    print("7. Manual memory operations (internal methods):")
    print("=" * 60)

    user_id = "user_123"

    # Store a specific memory using the shared memory tool
    memory_id = await long_term_memory.store_memory(
        user_id=user_id, content="User frequently visits his father in the countryside."
    )
    print(f"Stored memory with ID: {memory_id}")

    # Retrieve memories
    memories = await long_term_memory.retrieve_memories(user_id=user_id, query="travel plans", limit=1)
    print(f"Retrieved {len(memories)} memory about travel arrangements:")
    for memory in memories:
        print(f"  - {memory.content}")
    memories = await long_term_memory.retrieve_memories(user_id=user_id, query="parents", limit=1)
    print(f"Retrieved {len(memories)} memory about parents:")
    for memory in memories:
        print(f"  - {memory.content}")

    # Test internal methods (not available to agents)
    print("\n8. Testing internal methods (get_all_memories, delete_memory):")
    print("=" * 60)

    # Get all memories for user_123
    all_memories = await long_term_memory.get_all_memories(user_id)
    print(f"Total memories for user_123: {len(all_memories)}")
    for i, memory in enumerate(all_memories, 1):
        print(f"  {i}. {memory.content} (ID: {memory.memory_id})")

    # Test delete_memory
    if all_memories:
        memory_to_delete = all_memories[0]
        print(f"\nDeleting memory: {memory_to_delete.content}")
        success = await long_term_memory.delete_memory(user_id, memory_to_delete.memory_id)
        print(f"Delete successful: {success}")

        # Verify deletion
        remaining_memories = await long_term_memory.get_all_memories(user_id)
        print(f"Remaining memories: {len(remaining_memories)}")


if __name__ == "__main__":
    asyncio.run(main())
