from typing import Annotated, Any

from pydantic import PlainSerializer, PlainValidator


def _pydantic_hex_to_bytes(val: Any) -> bytes:  # noqa: ANN401
    """
    Deserialize hex string to bytes.
    """
    if isinstance(val, bytes):
        return val
    elif isinstance(val, bytearray):
        return bytes(val)
    elif isinstance(val, str):
        return bytes.fromhex(val)
    raise ValueError(f"Cannot convert {val} to bytes.")


def _pydantic_bytes_to_hex(val: bytes) -> str:
    """
    Serialize bytes to hex string.
    """
    return val.hex()


SerializableBytes = Annotated[
    bytes, PlainValidator(_pydantic_hex_to_bytes), PlainSerializer(_pydantic_bytes_to_hex, return_type=str)
]
