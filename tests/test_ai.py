import pytest
from unittest.mock import AsyncMock, patch
from server.schemas import MissionReq
from server.services.ai import generate_mission, validate_safety


def test_safety_filter_detects_banned_terms():
    assert validate_safety("Take a calm walk along the shaded park path.") is True
    assert validate_safety("Cross the road while looking at your screen for clues.") is False
    assert validate_safety("Enter the private property near the abandoned warehouse.") is False
    assert validate_safety("Follow the railway tracks past the signal station.") is False


@pytest.mark.asyncio
async def test_ai_valid_ollama_output_accepted():
    mock_payload = {
        "title": "Ancient Canopy Scout",
        "description": "Walk along the shaded pathway and observe natural canopy growth.",
        "est_minutes": 20,
        "intensity": "easy",
        "tip": "Enjoy the cool morning breeze.",
        "item_lore": "Dew drops linger where the canopy touches dawn."
    }

    with patch("server.services.ai.call_ollama", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_payload
        req = MissionReq(minutes=20, interest="trees", intensity="easy")
        resp = await generate_mission(req)
        assert resp.source == "gemma-local"
        assert resp.payload.title == "Ancient Canopy Scout"
        assert resp.payload.est_minutes == 20


@pytest.mark.asyncio
async def test_ai_unsafe_output_triggers_fallback():
    mock_unsafe = {
        "title": "Trespasser Sprint",
        "description": "Climb into private property and run across the highway.",
        "est_minutes": 20,
        "intensity": "moderate",
        "tip": "Ignore oncoming traffic.",
        "item_lore": "Hidden caches are inside restricted area."
    }

    with patch("server.services.ai.call_ollama", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_unsafe
        req = MissionReq(minutes=20, interest="urban", intensity="moderate")
        resp = await generate_mission(req)
        # Unsafe content rejected -> triggers fallback
        assert resp.source == "fallback"
        assert validate_safety(resp.payload.description) is True


@pytest.mark.asyncio
async def test_ai_ollama_offline_returns_fallback_gracefully():
    with patch("server.services.ai.call_ollama", new_callable=AsyncMock) as mock_call:
        # Simulate network error or Ollama down
        mock_call.return_value = None
        req = MissionReq(minutes=25, interest="nature", intensity="easy")
        resp = await generate_mission(req)
        assert resp.source == "fallback"
        assert resp.payload.title is not None
        assert len(resp.payload.description) >= 20
