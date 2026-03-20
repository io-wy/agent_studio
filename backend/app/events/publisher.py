"""Redis event pub/sub for real-time messaging"""
import asyncio
import json
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime

import redis.asyncio as redis

from app.core.config import settings


class EventPublisher:
    """Publish events to Redis"""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """Publish message to channel"""
        return await self.client.publish(channel, json.dumps(message))

    async def publish_event(
        self,
        event_type: str,
        resource_type: Optional[str],
        resource_id: Optional[str],
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Publish structured event"""
        event = {
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "payload": payload or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        # Publish to global channel
        await self.publish("events:global", event)
        # Also publish to resource-specific channel
        if resource_type and resource_id:
            await self.publish(f"events:{resource_type}:{resource_id}", event)
        # Publish to tenant channel
        if tenant_id:
            await self.publish(f"events:tenant:{tenant_id}", event)


class EventSubscriber:
    """Subscribe to events from Redis"""

    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def subscribe(self, channel: str) -> redis.client.PubSub:
        """Subscribe to channel"""
        self._pubsub = self.client.pubsub()
        await self._pubsub.subscribe(channel)
        return self._pubsub

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from channel"""
        if self._pubsub:
            await self._pubsub.unsubscribe(channel)

    async def listen(self, channel: str) -> AsyncIterator[Dict[str, Any]]:
        """Listen to channel messages"""
        pubsub = await self.subscribe(channel)
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    yield json.loads(message["data"])
                except json.JSONDecodeError:
                    yield {"raw": message["data"]}

    async def close(self) -> None:
        """Close connection"""
        if self._pubsub:
            await self._pubsub.close()
        if self._client:
            await self._client.close()


# Singleton instances
event_publisher = EventPublisher()
event_subscriber = EventSubscriber()


# Event type constants
class EventTypes:
    """Event type constants"""

    # Training
    TRAINING_JOB_QUEUED = "training_job.queued"
    TRAINING_JOB_RUNNING = "training_job.running"
    TRAINING_JOB_SUCCEEDED = "training_job.succeeded"
    TRAINING_JOB_FAILED = "training_job.failed"
    TRAINING_JOB_CANCELED = "training_job.canceled"

    # Deployment
    DEPLOYMENT_PROVISIONING = "deployment.provisioning"
    DEPLOYMENT_READY = "deployment.ready"
    DEPLOYMENT_FAILED = "deployment.failed"
    DEPLOYMENT_DELETED = "deployment.deleted"

    # Agent
    AGENT_RUN_QUEUED = "agent_run.queued"
    AGENT_RUN_RUNNING = "agent_run.running"
    AGENT_RUN_WAITING_TOOL = "agent_run.waiting_tool"
    AGENT_RUN_WAITING_HUMAN = "agent_run.waiting_human"
    AGENT_RUN_SUCCEEDED = "agent_run.succeeded"
    AGENT_RUN_FAILED = "agent_run.failed"
    AGENT_RUN_ABORTED = "agent_run.aborted"

    # Logs
    LOG_MESSAGE = "log.message"
