import asyncio
from distilabel.steps import StepInput
from distilabel.steps.base import Step


from ragbits.core.prompt import Prompt
from ragbits.core.llms.base import LLM
from copy import deepcopy
from ..prompts.corpus_generation import BasicCorpusGenerationPromptInput, BasicCorpusGenerationPrompt


class CorpusGenerationStep(Step):
    def __init__(self, llm: LLM, num_per_query: int, prompt_class: type[Prompt] = BasicCorpusGenerationPrompt, **kwargs):
        super().__init__(**kwargs)
        self._llm = llm
        self._prompt_class = prompt_class
        self._num_per_query = num_per_query

    @property
    def inputs(self) -> "StepColumns":
        return ["query"]

    @property
    def outputs(self) -> "StepColumns":
        return ["chunk"]

    def process(self, *inputs: StepInput) -> "StepOutput":
        result = []
        for inp in inputs[0]:
            for _ in range(self._num_per_query):
                new_inp = deepcopy(inp)
                prompt_inp = self._prompt_class.input_type(**{self.inputs[0]: new_inp[self.inputs[0]]})
                new_inp[self.outputs[0]] = asyncio.get_event_loop().run_until_complete(self._llm.generate(prompt=self._prompt_class(prompt_inp)))
                result.append(new_inp)
        yield result

