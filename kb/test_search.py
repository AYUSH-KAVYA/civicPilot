import asyncio
import json
from pathlib import Path

import pytest

from kb.search import policy_search
from kb.similar_cases import similar_cases


@pytest.mark.asyncio
async def test_policy_search_returns_department_sop():
    results = await policy_search("live fallen wire near school", "electricity", 4)
    assert results
    assert all(result["department_id"] == "electricity" for result in results)
    assert any("wire" in result["text"].lower() for result in results)


@pytest.mark.asyncio
async def test_dataset_has_expected_shape_and_counts():
    path = Path(__file__).parents[1] / "eval" / "datasets" / "grievances.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 60
    assert sum(len(case["text"]) < 35 for case in data) >= 10
    assert any(case["disruption"] == "duplicate_cluster" for case in data)
    assert all(case["simulated"] is True for case in data)


@pytest.mark.asyncio
async def test_similar_cases_returns_nearby_results():
    results = await similar_cases("pothole road", 28.614, 77.209, 2000, 5)
    assert isinstance(results, list)
