"""Log service - fetch and stream logs from Kubernetes"""
import re
from typing import AsyncIterator, Optional, List, Dict, Any
from datetime import datetime

from app.integrations.kubernetes import cluster_gateway


class LogService:
    """Service for fetching logs from Kubernetes"""

    async def get_pod_logs(
        self,
        namespace: str,
        pod_name: str,
        container: Optional[str] = None,
        tail_lines: int = 100,
        since_seconds: Optional[int] = None,
    ) -> str:
        """Get logs from a specific pod"""
        return await cluster_gateway.read_pod_logs(
            namespace=namespace,
            pod_name=pod_name,
            container=container,
            tail_lines=tail_lines,
        )

    async def get_deployment_logs(
        self,
        namespace: str,
        deployment_name: str,
        tail_lines: int = 100,
    ) -> Dict[str, str]:
        """Get logs from all pods in a deployment"""
        # Find pods by label
        pods = await cluster_gateway.read_pod_status(
            namespace=namespace,
            label_selector=f"app={deployment_name}",
        )

        logs = {}
        for pod in pods:
            logs[pod["name"]] = await cluster_gateway.read_pod_logs(
                namespace=namespace,
                pod_name=pod["name"],
                tail_lines=tail_lines,
            )

        return logs

    async def stream_pod_logs(
        self,
        namespace: str,
        pod_name: str,
        container: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream logs from a pod (simplified - real implementation would use k8s exec)"""
        # Simplified: just return current logs
        # Real implementation would use websocket to stream from k8s
        logs = await cluster_gateway.read_pod_logs(
            namespace=namespace,
            pod_name=pod_name,
            container=container,
            tail_lines=1000,
        )
        for line in logs.splitlines():
            yield f"{line}\n"

    async def get_training_job_logs(
        self,
        namespace: str,
        job_name: str,
        tail_lines: int = 100,
    ) -> str:
        """Get logs from training job pods"""
        pods = await cluster_gateway.read_pod_status(
            namespace=namespace,
            label_selector=f"job-name={job_name}",
        )

        if not pods:
            return "No pods found for this job"

        # Get logs from first pod
        pod = pods[0]
        return await cluster_gateway.read_pod_logs(
            namespace=namespace,
            pod_name=pod["name"],
            tail_lines=tail_lines,
        )

    async def get_agent_run_logs(
        self,
        namespace: str,
        run_id: str,
        tail_lines: int = 100,
    ) -> str:
        """Get logs from agent run pods"""
        pods = await cluster_gateway.read_pod_status(
            namespace=namespace,
            label_selector=f"run-id={run_id}",
        )

        if not pods:
            return "No pods found for this run"

        # Get logs from first pod
        pod = pods[0]
        return await cluster_gateway.read_pod_logs(
            namespace=namespace,
            pod_name=pod["name"],
            tail_lines=tail_lines,
        )

    async def search_logs(
        self,
        namespace: str,
        query: str,
        pod_pattern: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search logs across pods"""
        # Get all pods in namespace
        pods = await cluster_gateway.read_pod_status(namespace=namespace)

        results = []
        for pod in pods:
            if pod_pattern and not re.match(pod_pattern, pod["name"]):
                continue

            logs = await cluster_gateway.read_pod_logs(
                namespace=namespace,
                pod_name=pod["name"],
                tail_lines=1000,
            )

            # Simple search - find lines containing query
            for line in logs.splitlines():
                if query.lower() in line.lower():
                    results.append({
                        "pod": pod["name"],
                        "timestamp": pod.get("created"),
                        "message": line,
                    })

                    if len(results) >= limit:
                        return results

        return results


# Singleton instance
log_service = LogService()
