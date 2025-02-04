import asyncio
from typing import Generic, TypeVar

from ragbits.core.pipelines.pipeline import Pipeline, Step

InputT = TypeVar("InputT")


class MultiplicationStep(Step):
    """Multiply the input data by a factor"""

    def __init__(self, factor: int) -> None:
        self.factor = factor

    async def run(self, input_data: int) -> int:
        """Run the step"""
        return input_data * self.factor


class ToStringStep(Step):
    """Convert the input data to a string"""

    async def run(self, input_data: int) -> str:  # noqa: PLR6301
        """Run the step"""
        return str(input_data)


class AddExplanationStep(Step):
    """Add an explanation to the input data"""

    async def run(self, input_data: str) -> str:  # noqa: PLR6301
        """Run the step"""
        return f"{input_data} is the result of the multiplication"


class ToListOfWordsStep(Step):
    """Convert the input data to a list of words"""

    async def run(self, input_data: str) -> list[str]:  # noqa: PLR6301
        """Run the step"""
        return input_data.split(" ")


class JoinWithHeartsStep(Step):
    """Join the input data with hearts or return a message based on a boolean input"""

    async def run(self, data: list[str] | bool) -> str:  # noqa: PLR6301
        """Run the step"""
        if isinstance(data, bool):
            return "❤️ TRUE ❤️ " if data else "💔 FALSE 💔"
        return " ❤️ ".join(data)


class TeeStep(Step, Generic[InputT]):
    """Print the input data and return it"""

    async def run(self, input_data: InputT) -> InputT:  # noqa: PLR6301
        """Run the step"""
        print(input_data)
        return input_data


async def main() -> None:
    """
    Run the demo pipeline
    """
    pipeline = Pipeline[int, str](
        MultiplicationStep(2),
        MultiplicationStep(3),
        ToStringStep(),
        AddExplanationStep(),
        ToListOfWordsStep(),
        JoinWithHeartsStep(),
    )
    result = await pipeline.run(3)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
