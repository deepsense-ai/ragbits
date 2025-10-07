"""
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
    embedder = LiteLLMEmbedder(model_name="text-embedding-3-small")
    shared_vector_store = InMemoryVectorStore(embedder=embedder)
    llm = LiteLLM(model_name="gpt-4o-mini")

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

        long_term_memory = LongTermMemory(vector_store=shared_vector_store)

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

    # Manual memory operations (internal methods only)
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

    # Get all memories for user_123
    all_memories = await long_term_memory.get_all_memories(user_id)
    print(f"Total memories for user_123: {len(all_memories)}")
    for i, memory in enumerate(all_memories, 1):
        print(f"  {i}. {memory.content} (ID: {memory.memory_id})")

    # Delete memory
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


"""
Example output:

1. First conversation - storing information:
============================================================
Agent WITH Memory:
Response: I've noted that you love hiking in the mountains and that you're planning a trip to Rome next month!
If you need any tips or recommendations for either hiking or your trip to Rome, just let me know!

Agent WITHOUT Memory:
Response: I've noted that you love hiking in the mountains and that you're planning a trip to Rome next month.
If you'd like recommendations for hiking spots, activities in Rome, or anything else related to your interests,
just let me know!

------------------------------------------------------------

2. Second conversation - retrieving context:
============================================================
Agent WITH Memory:
Response: Since you're planning a trip to Rome next month and love hiking in the mountains,
here are some outdoor activities I would recommend:

1. **Hiking in the surrounding areas**: Consider day trips to the nearby hills, such as the **Castelli Romani**.
It's a beautiful area with great trails and stunning views.

2. **Exploring parks**: Spend some time in **Villa Borghese**, which is a large park in the city.
You can rent a bike or simply walk around and enjoy the gardens.

3. **Visit the Tiber River**: Take a stroll along the Tiber River.
There are plenty of areas to walk or cycle, plus you can stop for a drink or snack at one of the riverside cafes.

4. **Day trips**: If you’re up for a bit of travel,
consider visiting the **Abruzzo National Park** or the **Gran Sasso** mountains for more intense hiking experiences.

5. **Outdoor dining**: Enjoy al fresco dining at local trattorias,
which can be a delightful way to experience the local culture and cuisine in a pleasant setting.

Let me know if you need more detailed information or other suggestions!

Agent WITHOUT Memory:
Response: To suggest the best outdoor activities for your trip,
I’ll need to know the destination you're heading to and any specific interests you have,
like hiking, water sports, or wildlife watching.
Could you share more details?

------------------------------------------------------------

3. Different user (different memory key):
============================================================
Agent WITH Memory:
Response: Great to know that you love cooking Asian food! Do you have a favorite dish or recipe?

Agent WITHOUT Memory:
Response: Hi! It's great to hear that you love cooking Asian food! Do you have a favorite dish or cuisine?

------------------------------------------------------------

4. 2nd user asking about travel (should not know 1st user's info):
============================================================
Agent WITH Memory:
Response: I currently have a note about you loving to cook Asian food,
which might hint at a travel interest in visiting Asian countries to explore their culinary culture.
If there are more specific travel interests you'd like me to remember
or if you want to share more about your travel preferences, feel free to let me know!

Agent WITHOUT Memory:
Response: I don't have specific memories about your travel interests yet.
If you share some details about your preferences, favorite destinations, or types of travel experiences you enjoy,
I can remember that for future conversations!

------------------------------------------------------------

7. Manual memory operations (internal methods):
============================================================
Stored memory with ID: 6c2f8a4a-96ee-4b5d-9122-78358ea8d10d
Retrieved 1 memory about travel arrangements:
  - User is planning a trip to Rome next month.
Retrieved 1 memory about parents:
  - User frequently visits his father in the countryside.
Total memories for user_123: 3
  1. User loves hiking in the mountains. (ID: cbbbaf09-67ec-4b82-8447-d2d22c825a0f)
  2. User is planning a trip to Rome next month. (ID: 7731fd53-d275-4e9f-a0a3-e48ebc8664cf)
  3. User frequently visits his father in the countryside. (ID: 6c2f8a4a-96ee-4b5d-9122-78358ea8d10d)

Deleting memory: User loves hiking in the mountains.
Delete successful: True
Remaining memories: 2

"""
