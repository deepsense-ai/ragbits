import asyncio
import sys
from copy import deepcopy

from distilabel.steps import StepInput, StepOutput
from distilabel.steps.base import Step

from ragbits.core.llms.base import LLM
from ragbits.core.prompt import Prompt
from ragbits.core.utils.config_handling import import_by_path

module = sys.modules[__name__]


class CorpusGenerationStep(Step):
    """A step for corpus generation on given topics"""

    def __init__(
        self,
        llm: LLM,
        num_per_topic: int,
        prompt_class: str | type[Prompt],
    ):
        super().__init__()
        self._llm = llm
        self._prompt_class = import_by_path(prompt_class, module) if isinstance(prompt_class, str) else prompt_class
        self._num_per_topic = num_per_topic

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
        result = asyncio.get_event_loop().run_until_complete(self._process_topics(topics=inputs[0]))
        yield result

    async def _process_topics(self, topics: list[dict]) -> list[dict]:
        tasks = [self._process_topic(topic) for _ in range(self._num_per_topic) for topic in topics]
        results = await asyncio.gather(*tasks)
        return results

    async def _process_topic(self, topic: dict) -> dict:
        new_inp = deepcopy(topic)
        prompt_inp = self._prompt_class.input_type(**{self.inputs[0]: new_inp[self.inputs[0]]})  # type: ignore
        new_inp[self.outputs[0]] = await self._llm.generate(prompt=self._prompt_class(prompt_inp))
        return new_inp
