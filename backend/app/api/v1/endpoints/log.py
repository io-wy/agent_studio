"""Log endpoints"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.services.log import LogService
from app.security import get_current_user, TokenPayload

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/pods/{pod_name}")
async def get_pod_logs(
    pod_name: str,
    namespace: str = Query(..., description="Kubernetes namespace"),
    container: Optional[str] = Query(None, description="Container name"),
    tail_lines: int = Query(100, ge=1, le=10000, description="Number of lines to fetch"),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get logs from a specific pod"""
    service = LogService()
    logs = await service.get_pod_logs(
        namespace=namespace,
        pod_name=pod_name,
        container=container,
        tail_lines=tail_lines,
    )
    return {"pod": pod_name, "namespace": namespace, "logs": logs}


@router.get("/deployments/{deployment_name}")
async def get_deployment_logs(
    deployment_name: str,
    namespace: str = Query(..., description="Kubernetes namespace"),
    tail_lines: int = Query(100, ge=1, le=10000, description="Number of lines to fetch"),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get logs from all pods in a deployment"""
    service = LogService()
    logs = await service.get_deployment_logs(
        namespace=namespace,
        deployment_name=deployment_name,
        tail_lines=tail_lines,
    )
    return {"deployment": deployment_name, "namespace": namespace, "pods": logs}


@router.get("/training-jobs/{job_name}")
async def get_training_job_logs(
    job_name: str,
    namespace: str = Query(..., description="Kubernetes namespace"),
    tail_lines: int = Query(100, ge=1, le=10000, description="Number of lines to fetch"),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get logs from training job"""
    service = LogService()
    logs = await service.get_training_job_logs(
        namespace=namespace,
        job_name=job_name,
        tail_lines=tail_lines,
    )
    return {"job": job_name, "namespace": namespace, "logs": logs}


@router.get("/agent-runs/{run_id}")
async def get_agent_run_logs(
    run_id: str,
    namespace: str = Query(..., description="Kubernetes namespace"),
    tail_lines: int = Query(100, ge=1, le=10000, description="Number of lines to fetch"),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get logs from agent run"""
    service = LogService()
    logs = await service.get_agent_run_logs(
        namespace=namespace,
        run_id=run_id,
        tail_lines=tail_lines,
    )
    return {"run_id": run_id, "namespace": namespace, "logs": logs}


@router.get("/search")
async def search_logs(
    namespace: str = Query(..., description="Kubernetes namespace"),
    query: str = Query(..., description="Search query"),
    pod_pattern: Optional[str] = Query(None, description="Pod name regex pattern"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Search logs across pods"""
    service = LogService()
    results = await service.search_logs(
        namespace=namespace,
        query=query,
        pod_pattern=pod_pattern,
        limit=limit,
    )
    return {"query": query, "results": results}


@router.get("/stream/pods/{pod_name}")
async def stream_pod_logs(
    pod_name: str,
    namespace: str = Query(..., description="Kubernetes namespace"),
    container: Optional[str] = Query(None, description="Container name"),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Stream logs from a pod"""
    service = LogService()

    async def generate():
        async for line in service.stream_pod_logs(
            namespace=namespace,
            pod_name=pod_name,
            container=container,
        ):
            yield line

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
