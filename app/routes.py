from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.audit import AuditResponse
from app.schemas.event import EventIngestResponse, InboundEvent
from app.service import EventService
from app.storage.db import get_db_session

router = APIRouter()


@router.post("/events", response_model=EventIngestResponse)
async def ingest_event(
    payload: InboundEvent,
    session: AsyncSession = Depends(get_db_session),
) -> EventIngestResponse:
    return await EventService(session).ingest_event(payload)


@router.get("/audit/{user_id}", response_model=AuditResponse)
async def get_audit(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> AuditResponse:
    return await EventService(session).get_audit(user_id=user_id)
