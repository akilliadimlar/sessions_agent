from fastapi import APIRouter, HTTPException
from .logic import analyze_session
from .models import Session
# from .db import db  # MongoDB - commented out for testing with mock data
from .mock_db import mock_db

router = APIRouter()

@router.get("/analyze/{session_id}")
async def analyze(session_id: str):
    # session = await db.sessions.find_one({"_id": session_id})  # MongoDB version
    session = await mock_db.sessions.find_one({"_id": session_id})  # Mock data version
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    analysis = analyze_session(session)
    return analysis