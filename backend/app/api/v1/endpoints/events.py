"""WebSocket and SSE endpoints for real-time events"""
import asyncio
import json
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse

from app.security import get_current_user, TokenPayload

router = APIRouter(tags=["events"])


# === WebSocket ===

class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        # active_connections: dict[websocket, set[str]]
        self.active_connections: dict[WebSocket, set[str]] = {}

    async def connect(self, websocket: WebSocket, channels: List[str]):
        """Connect and subscribe to channels"""
        await websocket.accept()
        self.active_connections[websocket] = set(channels)

    def disconnect(self, websocket: WebSocket):
        """Disconnect"""
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)

    async def broadcast(self, message: dict, channel: Optional[str] = None):
        """Broadcast message to all clients subscribed to channel"""
        disconnected = []
        for websocket, channels in self.active_connections.items():
            if channel is None or channel in channels:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)

        for ws in disconnected:
            self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    channels: str = Query(default="", description="Comma-separated channels to subscribe"),
):
    """WebSocket endpoint for real-time events"""
    # Parse channels
    channel_list = [ch.strip() for ch in channels.split(",") if ch.strip()]
    if not channel_list:
        channel_list = ["events:global"]

    await manager.connect(websocket, channel_list)

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "channels": channel_list,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                # Handle ping/pong or commands
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass
            except asyncio.TimeoutError:
                # Send keep-alive ping
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# === SSE (Server-Sent Events) ===

async def sse_event_generator(
    channel: str,
    tenant_id: Optional[str] = None,
    project_id: Optional[str] = None,
):
    """Generate SSE events"""
    from app.events.publisher import event_subscriber

    try:
        # Subscribe to channel
        pubsub = await event_subscriber.subscribe(channel)

        # Send initial event
        yield f"event: connected\ndata: {json.dumps({'channel': channel})}\n\n"

        # Listen for messages
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    # Filter by tenant/project if specified
                    if tenant_id and data.get("tenant_id") != tenant_id:
                        continue
                    if project_id and data.get("project_id") != project_id:
                        continue
                    yield f"data: {message['data']}\n\n"
                except json.JSONDecodeError:
                    yield f"data: {json.dumps({'raw': message['data']})}\n\n"

    except asyncio.CancelledError:
        pass
    finally:
        await event_subscriber.unsubscribe(channel)


@router.get("/events/sse")
async def sse_endpoint(
    channel: str = Query(default="events:global", description="Channel to subscribe"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
):
    """SSE endpoint for real-time events"""
    return StreamingResponse(
        sse_event_generator(channel, tenant_id, project_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# === Event API ===

@router.post("/events/publish")
async def publish_event(
    event_type: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    project_id: Optional[str] = None,
    payload: Optional[dict] = None,
):
    """Publish an event (for internal use)"""
    from app.events.publisher import event_publisher

    await event_publisher.publish_event(
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        tenant_id=tenant_id,
        project_id=project_id,
        payload=payload,
    )

    return {"status": "published", "event_type": event_type}
