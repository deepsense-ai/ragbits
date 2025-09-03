# Tutorial: Building Intelligent Chat Interfaces with Agents

Let's build a **sophisticated chatbot interface** with **Ragbits Chat and Agents**. We'll create an intelligent chat system that uses AI agents to dynamically decide what enhancements to provide - no hardcoded rules, just intelligent decision-making.

**What you'll learn:**

- How to create an agent-powered chat interface that makes intelligent decisions
- How to use structured output with agents for consistent content generation
- How to dynamically generate references, images, and follow-ups based on context
- How to implement intelligent live updates that respond to query complexity
- How to build adaptive state management that learns from conversations
- How to configure smart user forms that evolve with user preferences
- How to create agents that customize responses based on user expertise
- How to debug and optimize agent-driven chat systems
- How to build production-ready intelligent assistants

Install the latest Ragbits via `pip install -U ragbits[agents]` and follow along.

## Configuring the environment

During development, we will use OpenAI's `gpt-4o-mini` model. To authenticate, Ragbits will look into your `OPENAI_API_KEY`. You can easily swap this out for [other providers](../how-to/llms/use_llms.md) or [local models](../how-to/llms/use_local_llms.md).

!!! tip "Recommended: Set up OpenTelemetry tracing to understand what's happening under the hood."
OpenTelemetry is an LLMOps tool that natively integrates with Ragbits and offer explainability and experiment tracking. In this tutorial, you can use OpenTelemetry to visualize prompts and optimization progress as traces to understand the Ragbits' behavior better. Check the full setup guide [here](../how-to/audit/use_tracing.md/#using-opentelemetry-tracer).

## Creating an Agent-Powered Chat Interface

The foundation of our intelligent chat system is the [`ChatInterface`][ragbits.chat.interface.ChatInterface] combined with **Ragbits Agents using tools** for decision-making. Following the Ragbits pattern, we'll use a **single agent with multiple tools** instead of multiple agents.

```python
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Literal, Optional

from pydantic import BaseModel, Field
from ragbits.agents import Agent
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatResponse, Message, LiveUpdateType
from ragbits.core.llms import LiteLLM, ToolCall, ToolCallResult
from ragbits.core.prompt import Prompt

# Define structured output for the agent's response
class Reference(BaseModel):
    title: str = Field(description="Title of the reference")
    content: str = Field(description="Brief description of what this reference contains")
    url: str = Field(description="URL to the reference")

class ImageSuggestion(BaseModel):
    should_include: bool = Field(description="Whether an image would be helpful")
    type: Optional[str] = Field(description="Type of image (diagram, chart, etc.)", default=None)
    description: Optional[str] = Field(description="What the image should show", default=None)

class ChatResponse(BaseModel):
    """Structured response from the agent with optional enhancements."""
    main_response: str = Field(description="The main text response to the user")
    references: list[Reference] = Field(description="Relevant references if helpful", default_factory=list)
    image_suggestion: Optional[ImageSuggestion] = Field(description="Image suggestion if helpful", default=None)
    followup_questions: list[str] = Field(description="Follow-up questions to continue the conversation", default_factory=list)

class ChatInput(BaseModel):
    message: str
    conversation_history: list[str] = Field(default_factory=list)

class ChatPrompt(Prompt[ChatInput, ChatResponse]):
    system_prompt = """
    You are an intelligent chat assistant. For each user message, provide a helpful response
    and decide whether to include enhancements like references, images, or follow-up questions.

    Guidelines:
    - Always provide a main_response answering the user's question
    - Add references only when they would genuinely help (credible sources, documentation, research)
    - Suggest images only when visual content would aid understanding (diagrams for complex concepts, charts for data, etc.)
    - Include follow-up questions that naturally extend the conversation based on the topic and context
    - Be intelligent about what enhancements add value vs. what feels forced

    Make decisions based on the content and context, not rigid rules.
    """

    user_prompt = """
    User message: {{ message }}

    {% if conversation_history %}
    Recent conversation: {{ conversation_history | join(" | ") }}
    {% endif %}

    Provide a helpful response with appropriate enhancements.
    """

class AgentPoweredChat(ChatInterface):
    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o", use_structured_output=True)

        # Agent with structured output - makes all decisions intelligently
        self.agent = Agent(
            llm=self.llm,
            prompt=ChatPrompt,
        )

    async def chat(
        self,
        message: str,
        history: list[Message] | None = None,
        context: dict | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        # Prepare input for the agent
        chat_input = ChatInput(
            message=message,
            conversation_history=[msg.get("content", "") for msg in (history or [])[-3:]]
        )

        # Get structured response from agent
        agent_response = await self.agent.run(chat_input)
        structured_response = agent_response.content

        # Stream the main text response
        yield self.create_text_response(structured_response.main_response)

        # Add references if the agent decided they're helpful
        for ref in structured_response.references:
            yield self.create_reference(
                title=ref.title,
                content=ref.content,
                url=ref.url
            )

        # Add image if the agent suggested one
        if structured_response.image_suggestion and structured_response.image_suggestion.should_include:
            img = structured_response.image_suggestion
            yield self.create_image_response(
                str(uuid.uuid4()),
                f"https://via.placeholder.com/500x300/4CAF50/FFFFFF?text={img.type or 'Image'}"
            )

        # Add follow-up questions if the agent provided them
        if structured_response.followup_questions:
            yield self.create_followup_messages(structured_response.followup_questions)
```

Save this code to a file called `agent_chat.py`.

!!! info "Intelligent Agent with Structured Output"
This approach is even better than tools - the agent uses **structured output** to make all decisions about content enhancements. No hardcoded logic, no tool parsing - just intelligent decisions.

    Key benefits:
    - **Pure Agent Intelligence**: Agent decides everything through structured output
    - **No Hardcoding**: References, images, and follow-ups are all agent-generated
    - **Context Aware**: Agent considers conversation history and user intent
    - **Flexible**: Agent can decide when NOT to include enhancements
    - **Clean Implementation**: No complex tool result parsing

!!! tip "Understanding the Flow" 1. User sends a message with conversation history 2. Agent analyzes everything and returns structured response 3. Agent decides: main text, references (if helpful), images (if useful), follow-ups (if relevant) 4. Chat interface uses agent's decisions to create appropriate UI elements 5. Everything is dynamic and contextual - no hardcoded rules!

## Starting the User Interface

Launch the agent-powered chat interface with the built-in web UI using the Ragbits CLI:

```bash
ragbits api run agent_chat:AgentPoweredChat
```

!!! note "Module Path Format"
The path should be the dotted Python _module path_ **without** the `.py` extension. For example, if your file is `agent_chat.py`, use `agent_chat:AgentPoweredChat`.

The server will start on **port 8000** by default. Open your browser and navigate to:

```
http://127.0.0.1:8000
```

You'll see an intelligent chat interface where the AI agent analyzes each message to determine what enhancements would be most helpful. Try asking complex questions like "How do machine learning algorithms work?" and watch how the agent decides whether to add live updates, references, or other enhancements.

## Customizing Agent Behavior

You can easily customize how the agent makes decisions by modifying the prompt and structured output models:

```python
# Add more specific fields to guide agent decisions
class EnhancedChatResponse(BaseModel):
    """Enhanced structured response with more control."""
    main_response: str = Field(description="The main text response to the user")
    references: list[Reference] = Field(description="Relevant references if helpful", default_factory=list)
    image_suggestion: Optional[ImageSuggestion] = Field(description="Image suggestion if helpful", default=None)
    followup_questions: list[str] = Field(description="Follow-up questions", default_factory=list)

    # Additional fields for more control
    response_tone: Literal["casual", "professional", "technical"] = Field(
        description="Appropriate tone for this response", default="professional"
    )
    complexity_level: Literal["beginner", "intermediate", "advanced"] = Field(
        description="Target complexity level", default="intermediate"
    )

class EnhancedChatPrompt(Prompt[ChatInput, EnhancedChatResponse]):
    system_prompt = """
    You are an intelligent chat assistant. Analyze each message and provide responses
    with appropriate enhancements based on context and user needs.

    Guidelines for decision-making:
    - For technical topics: Include references to documentation, tutorials, or research
    - For visual topics: Suggest diagrams, charts, or illustrations when they aid understanding
    - For learning conversations: Provide follow-up questions that deepen understanding
    - For quick questions: Keep enhancements minimal
    - For complex topics: Include comprehensive references and detailed follow-ups

    Always consider:
    - User's apparent expertise level from their question
    - Whether they're asking for specific information or general exploration
    - What would genuinely help them understand or learn more
    """

    user_prompt = """
    User message: {{ message }}

    {% if conversation_history %}
    Recent conversation: {{ conversation_history | join(" | ") }}
    {% endif %}

    Provide an intelligent response with contextually appropriate enhancements.
    """
```

This approach lets the agent make nuanced decisions about content, tone, and complexity based on the conversation context.

## Adding State Management and User Forms

Let's add intelligent state management and user preference forms to make our chat more personalized:

```python
from pydantic import ConfigDict
from ragbits.chat.interface.forms import FeedbackConfig, UserSettings
from ragbits.chat.interface.types import ChatContext
from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization

class UserPreferencesForm(BaseModel):
    model_config = ConfigDict(
        title="Chat Preferences",
        json_schema_serialization_defaults_required=True
    )

    expertise_level: Literal["Beginner", "Intermediate", "Expert"] = Field(
        description="Your technical expertise level",
        default="Intermediate"
    )
    preferred_detail: Literal["Brief", "Detailed", "Comprehensive"] = Field(
        description="How much detail do you prefer in responses?",
        default="Detailed"
    )

class IntelligentChatWithForms(ChatInterface):
    # Add user settings form
    user_settings = UserSettings(form=UserPreferencesForm)

    # Customize the UI
    ui_customization = UICustomization(
        header=HeaderCustomization(
            title="🤖 Smart Agent Assistant",
            subtitle="Powered by Ragbits Tools",
            logo="🛠️"
        ),
        welcome_message=(
            "Welcome to the Smart Agent Assistant! 🤖\n\n"
            "I use intelligent tools to enhance our conversation:\n"
            "- **Smart References** based on your questions\n"
            "- **Contextual Images** when they help explain concepts\n"
            "- **Relevant Follow-ups** that continue the discussion\n\n"
            "Try asking me about programming, science, or any topic you're curious about!"
        ),
    )

    conversation_history = True

    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini", use_structured_output=True)

        # Enhanced prompt that considers user preferences
        enhanced_prompt = ChatPrompt()
        enhanced_prompt.system_prompt += """

        Consider the user's expertise level and preferred detail level when responding:
        - Beginner: Use simple language and provide more context
        - Expert: Use technical terminology and be more concise
        - Brief: Keep responses focused and to-the-point
        - Comprehensive: Provide thorough explanations with examples
        """

        self.agent = Agent(
            llm=self.llm,
            prompt=enhanced_prompt,
            tools=[enhanced_generate_references, smart_suggest_image, contextual_followups],
        )

    async def chat(
        self,
        message: str,
        history: list[Message] | None = None,
        context: ChatContext | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        # Get user preferences and state
        current_state = context.state if context else {}
        user_prefs = context.user_settings if context else {}
        conversation_count = current_state.get("conversation_count", 0) + 1

        # Update state with conversation tracking
        updated_state = {
            "conversation_count": conversation_count,
            "last_topic": message[:50] + "..." if len(message) > 50 else message,
            "user_expertise": user_prefs.get("expertise_level", "Intermediate"),
        }
        yield self.create_state_update(updated_state)

        # Prepare enhanced input with user context
        conversation_history = [msg.get("content", "") for msg in (history or [])[-5:]]
        chat_input = ChatInput(
            message=message,
            conversation_history=conversation_history
        )

        # Stream responses from agent
        async for response in self.agent.run_streaming(chat_input):
            match response:
                case str():
                    yield self.create_text_response(response)
                case ToolCall():
                    yield self.create_live_update(
                        response.id,
                        LiveUpdateType.START,
                        f"🛠️ Using {response.name} tool",
                    )
                case ToolCallResult():
                    yield self.create_live_update(
                        response.id,
                        LiveUpdateType.FINISH,
                        f"✅ {response.name} completed",
                    )

                    # Process tool results
                    if response.name == "enhanced_generate_references":
                        refs = json.loads(response.result)
                        for ref in refs:
                            yield self.create_reference(
                                title=ref["title"],
                                content=ref["content"],
                                url=ref["url"]
                            )
                    elif response.name == "smart_suggest_image":
                        img_data = json.loads(response.result)
                        if img_data.get("should_include"):
                            yield self.create_image_response(
                                str(uuid.uuid4()),
                                f"https://via.placeholder.com/500x300/4CAF50/FFFFFF?text={img_data['type']}"
                            )
                    elif response.name == "contextual_followups":
                        followups = json.loads(response.result)
                        if followups:
                            yield self.create_followup_messages(followups)
```

This complete implementation demonstrates the proper Ragbits pattern: **one intelligent agent with multiple smart tools**.

## Enabling Debug Mode

Debug mode provides detailed information about the chat's internal state and is invaluable during development:

```bash
ragbits api run your_chat:IntelligentChatWithForms --debug
```

With debug mode enabled:

- A debug panel appears in the UI showing internal state
- Detailed logging information is available
- You can inspect tool calls, agent decisions, and response metadata
- Error information is more detailed and helpful

Additional server configuration options:

```bash
# Custom host and port
ragbits api run your_chat:YourChatClass --host 0.0.0.0 --port 9000

# Enable CORS for development
ragbits api run your_chat:YourChatClass --cors-origin http://localhost:3000
```

## Conclusions

In this tutorial, we've built a sophisticated chat interface using **intelligent agents with structured output** - the cleanest way to create dynamic, context-aware chat experiences.

### Key Features Implemented

- **🧠 Pure Agent Intelligence**: Agent makes all content decisions through structured output
- **📚 Dynamic References**: Agent-generated references based on context and relevance
- **🖼️ Contextual Images**: Agent decides when and what type of visuals would help
- **💭 Smart Follow-ups**: Agent creates questions that naturally extend conversations
- **📝 User Forms**: Feedback collection and preference settings
- **🎨 UI Customization**: Personalized interface with branding
- **⚡ Intelligent State**: Agent-aware state management and conversation tracking

### Why This Approach Works

1. **No Hardcoding**: Everything is decided by the agent - no rigid rules or conditional logic
2. **Context Awareness**: Agent considers conversation history, user intent, and topic complexity
3. **Flexible Decisions**: Agent can choose NOT to include enhancements when they're not helpful
4. **Natural Conversations**: Responses feel organic because they're intelligently crafted, not templated
5. **Easy to Extend**: Add new fields to structured output without changing core logic

### Next Steps

Now you can build intelligent chat interfaces that make smart decisions! You can:

- **Add More Tools**: Create tools for web search, code execution, or API calls
- **Enhance Prompts**: Improve agent decision-making with better prompts
- **Integrate Document Search**: Connect to [Document Search](./rag.md) for knowledge-based responses
- **Connect External APIs**: Use tools to integrate with databases and services

The key insight is simple: **use structured output to let the agent decide everything** - when to include references, what images would help, which follow-ups make sense. No hardcoded rules, no conditional logic, just intelligent agent decisions that create truly conversational experiences.

For more advanced configurations and deployment options, check out the [Chat API How-To Guide](../how-to/chatbots/api.md).
