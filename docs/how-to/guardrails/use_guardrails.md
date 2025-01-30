# How to use Guardrails

Ragbits offers an expandable guardrails system. You can use one of the available guardrails or create your own to prevent toxic language, PII leaks etc.

In this guide we will show you how to use guardrail based on OpenAI moderation and how to creat your own guardrail.


## Using existing guardrail
To use one of the existing guardrails you need to import it together with `GuardrailManager`. Next you simply pass a list of guardrails to the manager
and call `verify()` function that will check the input (`str` or `Prompt`) against all provided guardrails asynchronously.

```python
import asyncio
from ragbits.guardrails.base import GuardrailManager, GuardrailVerificationResult
from ragbits.guardrails.openai_moderation import OpenAIModerationGuardrail


async def verify_message(message: str) -> list[GuardrailVerificationResult]:
    manager = GuardrailManager([OpenAIModerationGuardrail()])
    return await manager.verify(message)


if __name__ == '__main__':
    print(asyncio.run(verify_message("Test message")))
```

The expected output is an object with the following properties:
```python
    guardrail_name: str
    succeeded: bool
    fail_reason: str | None
```
It allows you to see which guardrail was used, whether the check was successful and optionally a fail reason.

## Implementing custom guardrail
We need to create a new class that inherits from `Guardrail` and implements abstract method `verify`.

```python
from ragbits.core.prompt import Prompt
from ragbits.guardrails.base import Guardrail, GuardrailVerificationResult

class CustomGuardrail(Guardrail):

    async def verify(self, input_to_verify: Prompt | str) -> GuardrailVerificationResult:
        pass
```

With that you can pass your `CustomGuardrail` to the `GuardrailManager` as shown in [using existing guardrails section](#using-existing-guardrail).