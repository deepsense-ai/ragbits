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

import json
import re
import subprocess
import tempfile
from pathlib import Path

from ragbits.chat.providers import RagbitsChatModelProvider


def _make_all_fields_required(schema: dict[str, any]) -> dict[str, any]:
    """Recursively modify a JSON schema so that all object properties are required."""
    schema_type = schema.get("type")
    if schema_type == "object" and "properties" in schema:
        properties = schema["properties"]
        # Set all property names as required
        schema["required"] = list(properties.keys())
        # Recursively apply to all properties
        for prop_schema in properties.values():
            _make_all_fields_required(prop_schema)
        # Also handle additionalProperties if it's a schema
        if isinstance(schema.get("additionalProperties"), dict):
            _make_all_fields_required(schema["additionalProperties"])
    elif schema_type == "array" and "items" in schema:
        # Recursively apply to items
        _make_all_fields_required(schema["items"])
    # Recursively apply to allOf, anyOf, oneOf, not, if, then, else
    for key in ["allOf", "anyOf", "oneOf"]:
        if key in schema and isinstance(schema[key], list):
            for subschema in schema[key]:
                _make_all_fields_required(subschema)
    for key in ["not", "if", "then", "else"]:
        if key in schema and isinstance(schema[key], dict):
            _make_all_fields_required(schema[key])
    return schema


def _clean_schema_titles(schema: dict[str, any]) -> dict[str, any]:
    """Remove title fields that cause false type references."""
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


def _normalize_refs(schema: dict[str, any], ref_map: dict[str, str] = None) -> dict[str, any]:
    """Normalize $ref values to prevent duplicate type generation."""
    if ref_map is None:
        ref_map = {}

    if isinstance(schema, dict):
        if "$ref" in schema:
            ref_value = schema["$ref"]
            # Extract the type name from the reference
            if "#/$defs/" in ref_value:
                type_name = ref_value.split("#/$defs/")[-1]
                # Use the base type name without numbers
                base_name = type_name.rstrip("0123456789")
                if base_name != type_name:
                    # Replace numbered ref with base ref
                    schema["$ref"] = f"#/$defs/{base_name}"

        # Recursively process nested objects
        return {key: _normalize_refs(value, ref_map) for key, value in schema.items()}
    elif isinstance(schema, list):
        return [_normalize_refs(item, ref_map) for item in schema]
    else:
        return schema


def _prepare_schema(schema: dict[str, any]) -> dict[str, any]:
    """Wrapper function to prepare correct JSON schema for TypeScript generation."""
    required = _make_all_fields_required(schema)
    cleaned = _clean_schema_titles(required)
    normalized = _normalize_refs(cleaned)
    return normalized


def _replace_schema_form_types(typescript_code: str) -> str:
    """Replace generic objects with RJSFSchema where appropriate."""
    # Replace form fields with RJSFSchema
    replacements = [
        # Match form properties in config structures
        (r"(form\??:\s*)\{\s*\[k:\s*string\]:\s*unknown;\s*\}(\s*\|\s*null)?", r"\1RJSFSchema\2"),
    ]

    result = typescript_code
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.MULTILINE | re.DOTALL)

    return result


def _fix_duplicate_interface_names(typescript_content: str) -> str:
    """Fix numbered interface names like FeedbackItem1 -> FeedbackItem."""
    result = typescript_content

    patterns_to_fix = [
        (r"\bFeedbackItem\d+\b", "FeedbackItem"),
    ]

    for pattern, replacement in patterns_to_fix:
        result = re.sub(pattern, replacement, result)

    return result


def _generate_typescript_with_node(schema: dict[str, any], type_name: str) -> str:
    """Generate TypeScript interface using json-schema-to-typescript via subprocess."""
    try:
        # Clean up problematic title fields
        prepared_schema = _prepare_schema(schema)

        # Create a complete JSON Schema document
        full_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": type_name,
            **prepared_schema,
        }

        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_input:
            json.dump(full_schema, temp_input, indent=2)
            temp_input_path = temp_input.name

        try:
            # Run json-schema-to-typescript
            result = subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "npx",
                    "json-schema-to-typescript",
                    temp_input_path,
                    "--bannerComment",
                    "",  # Remove default banner
                    "--declareExternallyReferenced",
                    "false",
                    "--additionalProperties",
                    "false",
                    "--unknownAny",
                    "true",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            output = result.stdout.strip()
            output = _replace_schema_form_types(output)
            output = _fix_duplicate_interface_names(output)
            return output

        finally:
            # Clean up temporary file
            Path(temp_input_path).unlink(missing_ok=True)

    except subprocess.CalledProcessError as e:
        print(f"Error: json-schema-to-typescript failed for {type_name}: {e.stderr}")
        raise RuntimeError(f"Failed to generate TypeScript for {type_name}") from e
    except FileNotFoundError:
        print("Error: json-schema-to-typescript not found. Install with: npm install -g json-schema-to-typescript")
        raise RuntimeError("json-schema-to-typescript is required but not installed") from None


def _generate_chat_response_union_type() -> str:
    """Generate ChatResponse union type and specific response interfaces."""
    lines = []

    lines.append("/**")
    lines.append(" * Specific chat response types")
    lines.append(" */")

    # Generate specific response interfaces using new content wrapper types
    response_interfaces = [
        ("TextChatResponse", "text", "TextContent"),
        ("ReferenceChatResponse", "reference", "Reference"),
        ("MessageIdChatResponse", "message_id", "MessageIdContent"),
        ("ConversationIdChatResponse", "conversation_id", "ConversationIdContent"),
        ("StateUpdateChatResponse", "state_update", "ServerState"),
        ("LiveUpdateChatResponse", "live_update", "LiveUpdate"),
        ("FollowupMessagesChatResponse", "followup_messages", "FollowupMessagesContent"),
        ("ImageChatResponse", "image", "Image"),
        ("MessageUsageChatResponse", "usage", "UsageContent"),
        ("ClearMessageChatResponse", "clear_message", "unknown"),
        ("ConversationSummaryResponse", "conversation_summary", "ConversationSummaryContent"),
    ]

    internal_response_interfaces = [
        ("ChunkedChatResponse", "chunked_content", "ChunkedContent"),
    ]

    for interface_name, response_type, content_type in [*response_interfaces, *internal_response_interfaces]:
        lines.append(f"export interface {interface_name} {{")
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


def _generate_ts_enum_object(enum_name: str, enum_values: list[str]) -> str:
    lines = []
    lines.append("/**")
    lines.append(f" * Represents the {enum_name} enum")
    lines.append(" */")
    lines.append(f"export const {enum_name} = {{")
    for v in enum_values:
        camel_case = "".join(word.capitalize() if i > 0 else word.capitalize() for i, word in enumerate(v.split("_")))
        lines.append(f"    {camel_case}: '{v}',")
    lines.append("} as const;")
    lines.append("")
    lines.append(f"export type {enum_name} = TypeFrom<typeof {enum_name}>;")
    return "\n".join(lines)


def main() -> None:
    """Main function to generate TypeScript interfaces."""
    # Initialize model provider
    provider = RagbitsChatModelProvider()

    # Get enum and pydantic models separately
    enum_models = provider.get_enum_models()
    pydantic_models = provider.get_pydantic_models()

    # Combine all models
    all_models = {**enum_models, **pydantic_models}

    # Generate JSON Schema for all models
    schemas = {}
    for name, model in all_models.items():
        try:
            # Handle Python Enums differently from Pydantic models
            if hasattr(model, "__members__") and hasattr(model, "__name__"):
                # This is a Python Enum
                enum_values = [member.value for member in model]
                schema = {
                    "type": "string",
                    "enum": enum_values,
                    "description": f"Enum values: {', '.join(enum_values)}",
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

    # Add TypeFrom utility type if we have enums
    enum_names = list(enum_models.keys())
    if enum_names:
        lines.append("export type TypeFrom<T> = T[keyof T];")
        lines.append("")

    # Generate enums first (they might be referenced by interfaces)
    for name in enum_names:
        enum_values = schemas[name]["enum"]
        lines.append(_generate_ts_enum_object(name, enum_values))
        lines.append("")

    # Generate interfaces
    pydantic_names = list(pydantic_models.keys())
    for name in pydantic_names:
        lines.append(_generate_typescript_with_node(schemas[name], name))
        lines.append("")

    # Generate ChatResponse union type
    lines.append(_generate_chat_response_union_type())
    lines.append("")

    # Write to output file
    output_file = Path("typescript/@ragbits/api-client/src/autogen.types.ts")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated TypeScript interfaces in: {output_file}")
    print(f"Generated {len(enum_names)} enums and {len(pydantic_names)} interfaces")


if __name__ == "__main__":
    main()
