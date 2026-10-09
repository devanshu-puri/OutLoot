from fastapi import APIRouter
from server.schemas import MissionReq, MissionResp
from server.services.ai import generate_mission

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/mission", response_model=MissionResp)
async def create_mission_endpoint(req: MissionReq):
    return await generate_mission(req)
