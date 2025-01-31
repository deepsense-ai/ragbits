# How to integrate Promptfoo with Ragbits

Ragbits' `Prompt` abstraction can be seamlessly integrated with the `promptfoo` tool. After installing `promptfoo` as
specified in the [promptfoo documentation](https://www.promptfoo.dev/docs/installation/), you can generate promptfoo
configuration files for all the prompts discovered by our autodiscover mechanism by running the following command:

```bash
rbts prompts generate-promptfoo-configs
```

This command will generate a YAML files in the directory specified by `--target-path` (`promptfooconfigs` by
default). The generated file should look like this:

```yaml
prompts:
  - file:///path/to/your/prompt:PromptClass.to_promptfoo
```

You can then edit the generated file to add your custom `promptfoo` configurations. Once your `promptfoo` configuration
file is ready, you can run `promptfoo` with the following command:

```bash
promptfoo eval -c /path/to/generated/promptfoo-config.yaml
```

**Important: To ensure compatibility, make sure Node.js version 20 is installed.**
