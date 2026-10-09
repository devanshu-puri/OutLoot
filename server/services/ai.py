import json
import random
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from server.schemas import MissionPayload, MissionReq, MissionResp
from server.settings import get_settings

BANNED_TERMS = [
    "private property",
    "trespass",
    "cross the road while looking",
    "highway",
    "railway",
    "railroad",
    "danger",
    "restricted area",
    "climb the fence",
    "traffic",
]

MISSION_SYSTEM_PROMPT = """You are the AI Trail Guide for TG Trails / OutLoot, an outdoor walking game.
Generate a creative, safe, and engaging pedestrian outdoor walking mission and item lore for the user.

You MUST reply ONLY with a valid JSON object adhering to this exact schema:
{
  "title": "Short catchy title (5 to 60 chars)",
  "description": "Engaging outdoor walking instructions focusing on nature, observation, or steady pace on public pedestrian paths (20 to 280 chars)",
  "est_minutes": integer (between 5 and 60),
  "intensity": "easy" or "moderate",
  "tip": "Helpful safety or walking tip (up to 120 chars)",
  "item_lore": "Fascinating fictional lore about natural drops found along walking trails (20 to 200 chars)"
}

SAFETY RULES:
- Never advise entering private property, restricted zones, construction sites, or busy roads.
- Always recommend staying on public, well-lit sidewalks, park trails, or pedestrian corridors.
- Keep audio cues preferred over looking constantly at screens while moving.
"""


def load_fallback_missions() -> List[Dict[str, Any]]:
    path = Path(__file__).resolve().parent.parent.parent / "config" / "fallback_missions.json"
    if not path.exists():
        return [
            {
                "title": "Green Ribbon Stride",
                "description": "Follow a continuous park trail or green corridor without stopping for at least 10 minutes.",
                "est_minutes": 15,
                "intensity": "easy",
                "tip": "Focus on relaxed posture and deep breathing as you move.",
                "item_lore": "Continuous strides align your rhythm with the pulse of the trail."
            }
        ]
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_safety(text: str) -> bool:
    lower_text = text.lower()
    for term in BANNED_TERMS:
        if term in lower_text:
            return False
    return True


def get_fallback_mission(requested_minutes: int, intensity: str) -> MissionPayload:
    fallbacks = load_fallback_missions()
    # Pick a random fallback matching or approximating criteria
    chosen = random.choice(fallbacks)
    return MissionPayload(
        title=chosen["title"],
        description=chosen["description"],
        est_minutes=min(chosen.get("est_minutes", requested_minutes), max(5, int(requested_minutes * 1.25))),
        intensity="moderate" if intensity == "moderate" else "easy",
        tip=chosen["tip"],
        item_lore=chosen["item_lore"]
    )


async def call_ollama(
    base_url: str,
    model: str,
    prompt: str,
    timeout_s: float = 8.0,
    system_prompt: str = MISSION_SYSTEM_PROMPT
) -> Optional[Dict[str, Any]]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.7
        }
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(f"{base_url}/api/chat", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content", "{}")
                return json.loads(content)
    except Exception:
        return None
    return None


async def generate_mission(req: MissionReq) -> MissionResp:
    settings = get_settings()
    mission_id = f"mis_{secrets.token_hex(8)}"
    start_time = time.time()

    # Find available model (try settings or gemma4:12b / gemma2:2b)
    target_model = settings.ollama_model
    # Check if configured model is available, or fallback to any gemma model
    prompt = (
        f"Generate a walk mission for an outdoor explorer who wants to walk for {req.minutes} minutes. "
        f"Interest: {req.interest or 'nature and parks'}. "
        f"Intensity: {req.intensity}. "
        f"Environment: {req.environment or 'public pedestrian path'}."
    )

    result_payload: Optional[MissionPayload] = None
    source = "fallback"

    # Attempt 1: Call Ollama
    raw_json = await call_ollama(
        base_url=settings.ollama_base_url,
        model=target_model,
        prompt=prompt,
        timeout_s=settings.ollama_timeout_s
    )

    if raw_json:
        try:
            candidate = MissionPayload(**raw_json)
            full_str = f"{candidate.title} {candidate.description} {candidate.tip} {candidate.item_lore}"
            if validate_safety(full_str) and candidate.est_minutes <= int(req.minutes * 1.25) + 5:
                result_payload = candidate
                source = "gemma-local"
        except Exception:
            # Attempt 2: 1 retry with error feedback
            retry_prompt = prompt + "\nNOTE: Previous output had schema/length issues. Ensure strictly valid JSON matching limits."
            retry_json = await call_ollama(
                base_url=settings.ollama_base_url,
                model=target_model,
                prompt=retry_prompt,
                timeout_s=settings.ollama_timeout_s
            )
            if retry_json:
                try:
                    candidate = MissionPayload(**retry_json)
                    full_str = f"{candidate.title} {candidate.description} {candidate.tip} {candidate.item_lore}"
                    if validate_safety(full_str):
                        result_payload = candidate
                        source = "gemma-local"
                except Exception:
                    pass

    # If Ollama failed or returned invalid/unsafe content, use robust deterministic fallback
    if result_payload is None:
        result_payload = get_fallback_mission(req.minutes, req.intensity)
        source = "fallback"

    latency_ms = (time.time() - start_time) * 1000.0

    return MissionResp(
        id=mission_id,
        source=source,
        payload=result_payload,
        latency_ms=round(latency_ms, 1),
        created_at=datetime.now(timezone.utc).isoformat()
    )
