#!/usr/bin/env python3
"""
Script to generate TypeScript interfaces from JSON Schema generated from Pydantic models.

This script imports the Pydantic models from ragbits-chat, generates JSON Schema from them,
and then converts the JSON Schema to TypeScript interfaces using json-schema-to-typescript.

Requirements:
- Node.js and npm must be installed
- Install json-schema-to-typescript: npm install -g json-schema-to-typescript
- Or the script will use npx to auto-download if needed
"""

import sys
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

from ragbits.chat.interface.types import StateUpdate

# Add the packages directory to Python path so we can import ragbits modules
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "ragbits-chat" / "src"))


def import_ragbits_models():
    """Import core Pydantic models from ragbits-chat package."""
    try:
        from ragbits.chat.interface.types import (
            ChatContext,
            ChatRequest,
            ChatResponseType,
            ConfigResponse,
            FeedbackResponse,
            FeedbackType,
            LiveUpdate,
            LiveUpdateContent,
            LiveUpdateType,
            Message,
            MessageRole,
            Reference,
        )
        from ragbits.chat.interface.forms import FeedbackConfig, UserSettings
        from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization
        from ragbits.chat.api import FeedbackRequest

        return {
            # Enums
            "ChatResponseType": ChatResponseType,
            "FeedbackType": FeedbackType,
            "LiveUpdateType": LiveUpdateType,
            "MessageRole": MessageRole,

            # Core data models
            "ChatContext": ChatContext,
            "LiveUpdate": LiveUpdate,
            "LiveUpdateContent": LiveUpdateContent,
            "Message": Message,
            "Reference": Reference,
            "ServerState": StateUpdate,

            # API request/response models
            "ChatRequest": ChatRequest,
            "ConfigResponse": ConfigResponse,
            "FeedbackRequest": FeedbackRequest,
            "FeedbackResponse": FeedbackResponse,

            # Configuration models
            "FeedbackConfig": FeedbackConfig,
            "HeaderCustomization": HeaderCustomization,
            "UICustomization": UICustomization,
            "UserSettings": UserSettings,
        }
    except ImportError as e:
        print(f"Error importing ragbits models: {e}")
        print("Make sure you're running this from the project root and the ragbits-chat package is installed.")
        sys.exit(1)


def json_schema_to_typescript(schema: Dict[str, Any], type_name: str) -> str:
    """Convert JSON Schema to TypeScript interface using json-schema-to-typescript."""

    # Add missing fields for specific interfaces (custom logic)
    if type_name == "Message" and schema.get("type") == "object":
        properties = schema.get("properties", {})
        if "id" not in properties:
            schema = dict(schema)  # Make a copy
            schema.setdefault("properties", {})["id"] = {
                "type": "string",
                "description": "Optional message ID"
            }

    # Use the Node.js tool for better schema conversion
    return _generate_typescript_with_node(schema, type_name)


def _clean_schema_titles(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Remove problematic title fields that cause false type references."""
    if isinstance(schema, dict):
        cleaned = {}
        for key, value in schema.items():
            if key == "title" and isinstance(value, str):
                # Skip titles for primitive types that shouldn't become type references
                continue
            elif isinstance(value, dict):
                cleaned[key] = _clean_schema_titles(value)
            elif isinstance(value, list):
                cleaned[key] = [_clean_schema_titles(item) if isinstance(item, dict) else item for item in value]
            else:
                cleaned[key] = value
        return cleaned
    return schema


def _replace_schema_types(typescript_code: str) -> str:
    """Replace generic objects with RJSFSchema where appropriate."""

    # Replace form fields with RJSFSchema
    replacements = [
        # Match like_form, dislike_form, form fields with generic objects
        (r'(\w*_?form\??:\s*)\{\s*\[k:\s*string\]:\s*unknown;\s*\}(\s*\|\s*null)?', r'\1RJSFSchema\2'),

        # Match form properties in config structures
        (r'(form\??:\s*)\{\s*\[k:\s*string\]:\s*unknown;\s*\}(\s*\|\s*null)?', r'\1RJSFSchema\2'),
    ]

    result = typescript_code
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.MULTILINE | re.DOTALL)

    return result


def _generate_typescript_with_node(schema: Dict[str, Any], type_name: str) -> str:
    """Generate TypeScript interface using json-schema-to-typescript via subprocess."""
    try:
        # Clean up problematic title fields
        cleaned_schema = _clean_schema_titles(schema)

        # Create a complete JSON Schema document
        full_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": type_name,
            **cleaned_schema
        }

        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_input:
            json.dump(full_schema, temp_input, indent=2)
            temp_input_path = temp_input.name

        try:
            # Run json-schema-to-typescript
            result = subprocess.run([
                'npx', 'json-schema-to-typescript',
                temp_input_path,
                '--bannerComment', '',  # Remove default banner
                '--declareExternallyReferenced', 'false',
                '--additionalProperties', 'false'
            ],
            capture_output=True,
            text=True,
            check=True
            )

            # Clean up the output
            typescript_code = result.stdout.strip()

            # Remove any remaining banner comments and clean up
            lines = typescript_code.split('\n')
            cleaned_lines = []
            skip_banner = True

            for line in lines:
                if skip_banner and (line.startswith('/*') or line.startswith(' *') or line.startswith('*/')):
                    continue
                if skip_banner and line.strip() == '':
                    continue
                skip_banner = False
                cleaned_lines.append(line)

            # Apply post-processing to replace generic objects with RJSFSchema
            typescript_result = '\n'.join(cleaned_lines)
            return _replace_schema_types(typescript_result)

        finally:
            # Clean up temporary file
            Path(temp_input_path).unlink(missing_ok=True)

    except subprocess.CalledProcessError as e:
        print(f"Error: json-schema-to-typescript failed for {type_name}: {e.stderr}")
        raise RuntimeError(f"Failed to generate TypeScript for {type_name}")
    except FileNotFoundError:
        print(f"Error: json-schema-to-typescript not found. Install with: npm install -g json-schema-to-typescript")
        raise RuntimeError("json-schema-to-typescript is required but not installed")


def generate_chat_response_union_type() -> str:
    """Generate ChatResponse union type and specific response interfaces."""
    lines = []

    lines.append("/**")
    lines.append(" * Specific chat response types")
    lines.append(" */")

    # Generate specific response interfaces
    response_interfaces = [
        ("TextChatResponse", "text", "string"),
        ("ReferenceChatResponse", "reference", "Reference"),
        ("MessageIdChatResponse", "message_id", "string"),
        ("ConversationIdChatResponse", "conversation_id", "string"),
        ("StateUpdateChatResponse", "state_update", "ServerState"),
        ("LiveUpdateChatResponse", "live_update", "LiveUpdate"),
        ("FollowupMessagesChatResponse", "followup_messages", "string[]"),
    ]

    for interface_name, response_type, content_type in response_interfaces:
        lines.append(f"interface {interface_name} {{")
        lines.append(f"    type: '{response_type}'")
        lines.append(f"    content: {content_type}")
        lines.append("}")
        lines.append("")

    lines.append("/**")
    lines.append(" * Typed chat response union")
    lines.append(" */")
    lines.append("export type ChatResponse =")
    for interface_name, _, _ in response_interfaces:
        lines.append(f"    | {interface_name}")

    return "\n".join(lines)


def main():
    """Main function to generate TypeScript interfaces."""
    # Import models
    models = import_ragbits_models()

    # Generate JSON Schema for all models
    schemas = {}
    for name, model in models.items():
        try:
            # Handle Python Enums differently from Pydantic models
            if hasattr(model, '__members__') and hasattr(model, '__name__'):
                # This is a Python Enum
                enum_values = [member.value for member in model]
                schema = {
                    "type": "string",
                    "enum": enum_values,
                    "description": f"Enum values: {', '.join(enum_values)}"
                }
                schemas[name] = schema
            else:
                # This is a Pydantic model
                schema = model.model_json_schema()
                schemas[name] = schema
        except Exception as e:
            print(f"Warning: Could not generate schema for {name}: {e}")

    # Generate TypeScript content
    lines = []

    # Add file header
    lines.append("/**")
    lines.append(" * Auto-generated TypeScript interfaces from Python Pydantic models")
    lines.append(" * Generated by scripts/generate_typescript_from_json_schema.py")
    lines.append(" * DO NOT EDIT MANUALLY")
    lines.append(" */")
    lines.append("")

    # Add imports
    lines.append("import type { RJSFSchema } from '@rjsf/utils';")
    lines.append("")

    # Generate enums first (they might be referenced by interfaces)
    enum_names = []
    interface_names = []

    for name, schema in schemas.items():
        if schema.get("type") == "string" and "enum" in schema:
            enum_names.append(name)
        else:
            interface_names.append(name)

    # Generate enums
    for name in sorted(enum_names):
        lines.append(json_schema_to_typescript(schemas[name], name))
        lines.append("")

    # Generate interfaces
    for name in sorted(interface_names):
        lines.append(json_schema_to_typescript(schemas[name], name))
        lines.append("")

    # Generate ChatResponse union type
    lines.append(generate_chat_response_union_type())
    lines.append("")

    # Write to output file
    output_file = Path("typescript/@ragbits/api-client/src/autogentypes.ts")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated TypeScript interfaces in: {output_file}")
    print(f"Generated {len(enum_names)} enums and {len(interface_names)} interfaces")


if __name__ == "__main__":
    main()