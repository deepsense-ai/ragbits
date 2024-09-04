from ragnarok_dev_kit.discovery.prompt_discovery import PromptDiscovery


def test_prompt_discovery_A():
    test_paths = ["prompt_classes_for_tests.py"]

    test_discovery_object = PromptDiscovery(test_paths).discover()

    assert len(test_discovery_object.keys()) == 4

    assert "PromptForTest" in test_discovery_object.keys()
    assert test_discovery_object["PromptForTest"]["user_prompt"] == "fake user prompt"
    assert test_discovery_object["PromptForTest"]["system_prompt"] == "fake system prompt"
    assert len(test_discovery_object["PromptForTest"]["input_type"].model_fields) == 6

    assert "PromptForTest2" in test_discovery_object.keys()
    assert test_discovery_object["PromptForTest2"]["user_prompt"] == "fake user prompt2"
    assert test_discovery_object["PromptForTest2"]["system_prompt"] == "fake system prompt2"
    assert len(test_discovery_object["PromptForTest2"]["input_type"].model_fields) == 1

    assert "MyPromptWithBase" in test_discovery_object.keys()
    assert test_discovery_object["MyPromptWithBase"]["user_prompt"] == "custom user prompt"
    assert test_discovery_object["MyPromptWithBase"]["system_prompt"] == "my base system prompt"


def test_prompt_discovery_B():
    test_paths = ["ragnarok_common"]

    test_discovery_object = PromptDiscovery(test_paths).discover()

    assert len(test_discovery_object.keys()) == 1

    assert "LoremPrompt" in test_discovery_object.keys()
