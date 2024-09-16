import sys
from pathlib import Path

from ragbits.dev_kit.discovery.prompt_discovery import PromptDiscovery


def test_prompt_discovery_from_file():
    test_paths = ["prompt_classes_for_tests.py"]

    discovery_result = PromptDiscovery(test_paths).discover()

    assert len(discovery_result.keys()) == 4

    assert "PromptForTest" in discovery_result.keys()
    assert discovery_result["PromptForTest"]["user_prompt"] == "fake user prompt"
    assert discovery_result["PromptForTest"]["system_prompt"] == "fake system prompt"
    assert len(discovery_result["PromptForTest"]["input_type"].model_fields) == 6

    assert "PromptForTest2" in discovery_result.keys()
    assert discovery_result["PromptForTest2"]["user_prompt"] == "fake user prompt2"
    assert discovery_result["PromptForTest2"]["system_prompt"] == "fake system prompt2"
    assert len(discovery_result["PromptForTest2"]["input_type"].model_fields) == 1

    assert "MyPromptWithBase" in discovery_result.keys()
    assert discovery_result["MyPromptWithBase"]["user_prompt"] == "custom user prompt"
    assert discovery_result["MyPromptWithBase"]["system_prompt"] == "my base system prompt"


def test_prompt_discovery_from_package():
    sys.path.append(str(Path(__file__).parent))
    test_paths = ["ragbits_tests_pkg_with_prompts"]

    discovery_result = PromptDiscovery(test_paths).discover()

    assert len(discovery_result.keys()) == 2

    assert "PromptForTestA" in discovery_result
    assert "PromptForTestB" in discovery_result
