# How-To: Stream events from tools

In this document, we will build a tool that is able to send custom commands to the UI and display a Markdown table
to the user.

## Define a streaming tool
To achieve this, define a tool as a `Generator` or `AsyncGenerator` that yields an event that the client is able
to handle. In our case, we will use a `TextReponse` event, which is supported by Ragbits UI.

Note, that the custom events yielded from the tool won't be automatically passed to the LLM. To indicate the output of
the tool that needs to be passed to the LLM, use `ToolReturn`.

```python
from collections.abc import Generator

from ragbits.agents.tool import ToolReturn
from ragbits.chat.interface.types import TextContent, TextResponse

--8<-- "examples/agents/stream_events_from_tools.py:61:75"
```

You can also define custom events by inheriting `ChatResponse` class with a custom `ResponseContent`. The content can
be arbitrary, as long as your client understands it and is able to handle it. To do that, you will need to extend
Ragbits UI with your own event handlers.

## Use it in a ChatInterface

Now, we will implement a [`ChatInterface`][ragbits.chat.interface.ChatInterface] that uses the agent with the streaming tool.
You can serve and test it via `RagbitsAPI`. Since we used a TextResponse that is understood by the Ragbits UI, we can
deploy the app and test the agent right away.

```python
from collections.abc import AsyncGenerator

from ragbits.agents import Agent
from ragbits.chat.api import RagbitsAPI
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse, TextResponse
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt.base import ChatFormat

--8<-- "examples/agents/stream_events_from_tools.py:82:111"
```
