import asyncio
import sys
from copy import deepcopy

from distilabel.steps import StepInput, StepOutput
from distilabel.steps.base import Step

from ragbits.core.llms.base import LLM
from ragbits.core.prompt import Prompt
from ragbits.core.utils.config_handling import get_cls_from_config

module = sys.modules[__name__]


class CorpusGenerationStep(Step):
    """A step for corpus generation on given topics"""

    def __init__(
        self,
        llm: LLM,
        num_per_query: int,
        prompt_class: str | type[Prompt],
    ):
        super().__init__()
        self._llm = llm
        self._prompt_class = (
            get_cls_from_config(prompt_class, module) if isinstance(prompt_class, str) else prompt_class
        )
        self._num_per_query = num_per_query

    @property
    def inputs(self) -> list[str]:
        """
        A property defining input fields for a task
        Returns:
            list of input fields
        """
        return ["query"]

    @property
    def outputs(self) -> list[str]:
        """
        A property describing output fields for a step
        Returns:
            list of output fields
        """
        return ["chunk"]

    def process(self, *inputs: StepInput) -> "StepOutput":
        """
        Generates the corpus data for a given topics
        Args:
            inputs: a topics on which the corpus data should be generated
        Returns:
            a generated corpus
        """
        result = []
        for inp in inputs[0]:
            for _ in range(self._num_per_query):
                new_inp = deepcopy(inp)
                prompt_inp = self._prompt_class.input_type(**{self.inputs[0]: new_inp[self.inputs[0]]}) #type: ignore
                new_inp[self.outputs[0]] = asyncio.get_event_loop().run_until_complete(
                    self._llm.generate(prompt=self._prompt_class(prompt_inp))
                )
                result.append(new_inp)
        yield result
