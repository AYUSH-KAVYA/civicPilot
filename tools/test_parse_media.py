import asyncio

import pytest

from tools.parse_media import parse_media


@pytest.mark.asyncio
async def test_vague_report_requests_location_and_lower_confidence():
    result = await parse_media("help", [], None)
    assert "location" in result["missing_info"]
    assert result["confidence"] < 0.65


@pytest.mark.asyncio
async def test_parser_extracts_category_and_sensitive_site():
    result = await parse_media(
        "A live wire fell near the hospital and road is blocked",
        ["https://example.test/photo.jpg"],
        "en",
    )
    assert result["category"] == "electricity"
    assert "hospital" in result["nearby_sensitive_sites"]
    assert result["visible_damage"]
