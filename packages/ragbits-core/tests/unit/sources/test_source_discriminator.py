from pathlib import Path
from typing import Annotated

import pydantic
import pytest

from ragbits.core.sources.base import Source, SourceDiscriminator
from ragbits.core.sources.local import LocalFileSource


class ModelWithSource(pydantic.BaseModel):
    source: Annotated[Source, SourceDiscriminator()]
    foo: str


def test_serialization():
    source = LocalFileSource(path=Path("test"))
    model = ModelWithSource(source=source, foo="bar")
    assert model.model_dump() == {
        "source": {
            "source_type": "local_file_source",
            "path": Path("test"),
        },
        "foo": "bar",
    }
    assert model.model_dump_json() == '{"source":{"path":"test","source_type":"local_file_source"},"foo":"bar"}'


def test_deserialization_from_json():
    json = '{"source":{"path":"test","source_type":"local_file_source"},"foo":"bar"}'
    model = ModelWithSource.model_validate_json(json)
    assert isinstance(model.source, LocalFileSource)
    assert model.source.path == Path("test")
    assert model.foo == "bar"


def test_deserialization_from_dict():
    dict = {
        "source": {
            "source_type": "local_file_source",
            "path": Path("test"),
        },
        "foo": "bar",
    }
    model = ModelWithSource.model_validate(dict)
    assert isinstance(model.source, LocalFileSource)
    assert model.source.path == Path("test")
    assert model.foo == "bar"


def test_deserialization_from_dict_with_invalid_source():
    dict = {
        "source": {
            "source_type": "invalid_source",
            "path": Path("test"),
        },
        "foo": "bar",
    }
    with pytest.raises(pydantic.ValidationError) as e:
        ModelWithSource.model_validate(dict)
    assert e.match("source")


def test_deserialization_from_dict_with_missing_source_type():
    dict = {
        "source": {
            "path": Path("test"),
        },
        "foo": "bar",
    }
    with pytest.raises(pydantic.ValidationError) as e:
        ModelWithSource.model_validate(dict)
    assert e.match("source")
