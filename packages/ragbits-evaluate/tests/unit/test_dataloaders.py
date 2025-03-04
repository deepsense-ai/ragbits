import pytest
import pytest_asyncio
import pandas as pd
import json
from pathlib import Path
from datasets import Dataset

from ragbits.evaluate.dataloaders.hf import HFDataLoader
from ragbits.evaluate.dataloaders.local import LocalDataLoader


@pytest.fixture(params=["json", "csv", "parquet"])
def temp_data_file(request, tmp_path):
    """Generate temporary test files in different formats"""
    data = [{"text": "Hello world", "label": 0}, {"text": "Test example", "label": 1}]
    df = pd.DataFrame(data)
    file_path = tmp_path / f"test_data.{request.param}"

    if request.param == "json":
        with open(file_path, "w") as f:
            json.dump(data, f)
    elif request.param == "csv":
        df.to_csv(file_path, index=False)
    elif request.param == "parquet":
        df.to_parquet(file_path)

    return str(file_path)


@pytest_asyncio.fixture
async def test_dataset():
    """Path to test dataset in hf hub"""
    return "deepsense-ai/synthetic-rag-dataset_v1.0"


@pytest.mark.asyncio
async def test_hf_data_loader(test_dataset):
    loader = HFDataLoader(path=test_dataset, split="train")
    result = await loader.load()
    assert isinstance(result, Dataset)


@pytest.mark.asyncio
async def test_local_data_loader(temp_data_file):
    loader = LocalDataLoader(
        path=temp_data_file,
        split="train",
        builder=Path(temp_data_file).suffix[1:],  # Extract format from extension
    )

    result = await loader.load()
    assert isinstance(result, Dataset)
    assert len(result) == 2
