from abc import ABC, abstractmethod
from types import UnionType
from typing import Generic, TypeVar, Union, cast, get_type_hints

from generics import get_filled_type
from typing_utils import Type, issubtype

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class Step(ABC, Generic[InputT, OutputT]):
    """
    A step in a pipeline that processes input data and returns output data
    """

    @abstractmethod
    async def run(self, /, input_data: InputT) -> OutputT:
        """
        Run the step with the given input data
        """


class Pipeline(Step[InputT, OutputT]):
    """
    A pipeline that consists of multiple steps that process input data and return output data
    """

    def __init__(self, *steps: Step) -> None:
        self.steps = steps
        self._validate_intrastep_types()

    @staticmethod
    def _issubtype(needed_type: Type, actual_type: Type) -> bool:
        """
        Check if the actual type is a subtype of the needed type.
        """
        # Covert new union type syntax to Union objects, as typing_utils.issubtype
        # does not support the new syntax
        if isinstance(needed_type, UnionType):
            needed_type = Union[tuple(needed_type.__args__)]  # noqa: UP007
        if isinstance(actual_type, UnionType):
            actual_type = Union[tuple(actual_type.__args__)]  # noqa: UP007
        return issubtype(needed_type, actual_type)

    def _validate_intrastep_types(self) -> None:
        """
        Validate that the output type of each step is compatible with the input type of the next step.

        Doesn't validate the first step input type and the last step output type because those are not know
        durint the initialization of the pipeline (due to the generic types and the specifics
        of the Python typing system).
        """
        for i, step in enumerate(self.steps):
            if i == 0:
                continue
            prev_step = self.steps[i - 1]
            previous_output_type = get_type_hints(prev_step.run).get("return")
            input_type = list(get_type_hints(step.run).values())[0]

            # print(f"Step {i - 1} output type: {previous_output_type}")
            # print(f"Step {i} input type: {input_type}")
            if not self._issubtype(previous_output_type, input_type):
                raise TypeError(
                    f"Step {i} input type {input_type} is not compatible with "
                    "previous step output type {previous_output_type}"
                )

    def _validate_input_output_types(self, input_type: Type, output_type: Type) -> None:
        """
        Validate that the input type of the pipeline is compatible with the first step input type and
        that the output type of the pipeline is compatible with the last step output type.
        """
        if not self.steps:
            if not self._issubtype(input_type, output_type):
                raise TypeError(
                    f"Pipeline has no steps and input type {input_type} "
                    "is not compatible with output type {output_type}",
                )
            return

        first_step_input_type = list(get_type_hints(self.steps[0].run).values())[0]
        last_step_output_type = get_type_hints(self.steps[-1].run).get("return")

        if not self._issubtype(first_step_input_type, input_type):
            raise TypeError(
                f"First step input type {first_step_input_type} is not compatible with pipeline input type {input_type}"
            )
        if not self._issubtype(output_type, last_step_output_type):
            raise TypeError(
                f"Last step output type {last_step_output_type} is not compatible with "
                "pipeline output type {output_type}"
            )

    async def run(self, input_data: InputT) -> OutputT:
        """
        Run the pipeline with the given input data and return the output data
        """
        input_type = get_filled_type(self, Pipeline, 0)
        output_type = get_filled_type(self, Pipeline, 1)
        self._validate_input_output_types(input_type, output_type)

        for step in self.steps:
            input_data = await step.run(input_data)

        return cast(OutputT, input_data)
