# api/routes/chainboard_realtime.py
"""
ChainBoard Real-Time Routes
============================

Server-Sent Events (SSE) endpoint for live Control Tower updates.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.realtime.bus import event_stream

router = APIRouter(prefix="/api/chainboard", tags=["chainboard-realtime"])


async def _sse_event_generator():
    """
    SSE frame generator.

    Yields events in SSE format: "data: <json>\\n\\n"
    """
    async for event in event_stream():
        data = event.model_dump_json()
        # SSE frame format: data line followed by blank line
        yield f"data: {data}\n\n"


@router.get("/events/stream")
async def stream_events():
    """
    Server-Sent Events endpoint for real-time Control Tower updates.

    Browser clients can connect with EventSource API.
    Events are streamed as JSON in SSE format.

    Returns:
        StreamingResponse with text/event-stream media type
    """
    return StreamingResponse(
        _sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
