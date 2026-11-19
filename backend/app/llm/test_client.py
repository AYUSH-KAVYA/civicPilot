import pytest
from pydantic import BaseModel

from backend.app.llm.client import GeminiClient


class DemoModel(BaseModel):
    confidence: float
    version: int


@pytest.mark.asyncio
async def test_mock_generate_json_is_deterministic():
    llm = GeminiClient({"MOCK_LLM": "true"})
    first = await llm.generate_json([{"role": "user", "content": "test"}], DemoModel)
    second = await llm.generate_json([{"role": "user", "content": "test"}], DemoModel)
    assert first == second
    assert 0 <= first.confidence <= 1


@pytest.mark.asyncio
async def test_mock_embed_is_deterministic():
    llm = GeminiClient({"MOCK_LLM": "true"})
    one = await llm.embed(["same text"])
    two = await llm.embed(["same text"])
    assert one == two
    assert len(one[0]) == 32
