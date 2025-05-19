from pathlib import Path

from ragbits.core.prompt.discovery import PromptDiscovery

current_dir = Path(__file__).parent


def test_prompt_discovery_from_file():
    discovery_results = PromptDiscovery(root_path=current_dir).discover()
    print(discovery_results)

    assert len(discovery_results) == 5

    class_names = [cls.__name__ for cls in discovery_results]
    assert "PromptForTest" in class_names
    assert "PromptForTest2" in class_names
    assert "PromptWithoutInput" in class_names
    assert "PromptForTestInput" not in class_names


def test_prompt_discovery_from_package():
    discovery_results = PromptDiscovery(
        root_path=current_dir, file_pattern="ragbits_tests_pkg_with_prompts/**/*.py"
    ).discover()

    assert len(discovery_results) == 2

    class_names = [cls.__name__ for cls in discovery_results]
    assert "PromptForTestA" in class_names
    assert "PromptForTestB" in class_names
