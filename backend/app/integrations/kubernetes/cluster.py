"""Kubernetes cluster gateway"""
import asyncio
from typing import Optional, List, Dict, Any

import yaml
from kubernetes import client, config
from kubernetes.client import ApiClient
from kubernetes.client.models import V1Job, V1Service, V1Deployment, V1Namespace, V1Ingress
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class ClusterGateway:
    """Kubernetes cluster integration"""

    def __init__(self):
        self._client: Optional[ApiClient] = None
        self._core_v1: Optional[client.CoreV1Api] = None
        self._batch_v1: Optional[client.BatchV1Api] = None
        self._apps_v1: Optional[client.AppsV1Api] = self._get_apps_v1()
        self._networking_v1: Optional[client.NetworkingV1Api] = None

    def _get_core_v1(self) -> client.CoreV1Api:
        if self._core_v1 is None:
            self._load_config()
            self._core_v1 = client.CoreV1Api()
        return self._core_v1

    def _get_batch_v1(self) -> client.BatchV1Api:
        if self._batch_v1 is None:
            self._load_config()
            self._batch_v1 = client.BatchV1Api()
        return self._batch_v1

    def _get_apps_v1(self) -> client.AppsV1Api:
        if self._apps_v1 is None:
            self._load_config()
            self._apps_v1 = client.AppsV1Api()
        return self._apps_v1

    def _get_networking_v1(self) -> client.NetworkingV1Api:
        if self._networking_v1 is None:
            self._load_config()
            self._networking_v1 = client.NetworkingV1Api()
        return self._networking_v1

    def _load_config(self):
        """Load Kubernetes config"""
        try:
            # Try in-cluster config first
            config.load_incluster_config()
        except Exception:
            # Fall back to local config
            try:
                config.load_kube_config()
            except Exception as e:
                raise RuntimeError(f"Failed to load Kubernetes config: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def create_namespace(self, namespace: str, labels: Optional[Dict[str, str]] = None) -> V1Namespace:
        """Create namespace with quotas"""
        core_v1 = self._get_core_v1()

        ns_body = V1Namespace(
            metadata=client.V1ObjectMeta(
                name=namespace,
                labels=labels or {"app": "agent-studio"},
            )
        )

        try:
            return core_v1.create_namespace(body=ns_body)
        except client.exceptions.ApiException as e:
            if e.status == 409:  # Already exists
                return core_v1.read_namespace(name=namespace)
            raise

    async def apply_manifest(self, manifest: Dict[str, Any]) -> Any:
        """Apply a Kubernetes manifest"""
        # Simplified - just use core operations
        kind = manifest.get("kind", "").lower()
        api_version = manifest.get("apiVersion", "")

        if kind == "namespace":
            return await self.create_namespace(
                manifest["metadata"]["name"],
                manifest["metadata"].get("labels"),
            )
        elif kind == "job":
            return self._get_batch_v1().create_namespaced_job(
                namespace=manifest["metadata"]["namespace"],
                body=manifest,
            )
        elif kind == "service":
            return self._get_core_v1().create_namespaced_service(
                namespace=manifest["metadata"]["namespace"],
                body=manifest,
            )
        elif kind == "deployment":
            return self._get_apps_v1().create_namespaced_deployment(
                namespace=manifest["metadata"]["namespace"],
                body=manifest,
            )
        else:
            raise ValueError(f"Unsupported kind: {kind}")

    async def read_pod_status(self, namespace: str, label_selector: str = None) -> List[Dict[str, Any]]:
        """Read pod status in namespace"""
        core_v1 = self._get_core_v1()
        try:
            pods = core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=label_selector,
            )
            return [
                {
                    "name": pod.metadata.name,
                    "status": pod.status.phase,
                    "node": pod.spec.node_name,
                    "ip": pod.status.pod_ip,
                    "created": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                }
                for pod in pods.items
            ]
        except client.exceptions.ApiException as e:
            if e.status == 404:
                return []
            raise

    async def read_pod_logs(
        self,
        namespace: str,
        pod_name: str,
        container: Optional[str] = None,
        tail_lines: int = 100,
    ) -> str:
        """Read pod logs"""
        core_v1 = self._get_core_v1()
        try:
            logs = core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines,
            )
            return logs
        except client.exceptions.ApiException as e:
            if e.status == 404:
                return "Pod not found"
            raise

    async def delete_workload(self, kind: str, name: str, namespace: str) -> bool:
        """Delete a workload (job, deployment, etc.)"""
        try:
            if kind.lower() == "job":
                self._get_batch_v1().delete_namespaced_job(
                    name=name,
                    namespace=namespace,
                    body=client.V1DeleteOptions(propagation_policy="Foreground"),
                )
            elif kind.lower() == "deployment":
                self._get_apps_v1().delete_namespaced_deployment(
                    name=name,
                    namespace=namespace,
                    body=client.V1DeleteOptions(propagation_policy="Foreground"),
                )
            elif kind.lower() == "service":
                self._get_core_v1().delete_namespaced_service(
                    name=name,
                    namespace=namespace,
                    body=client.V1DeleteOptions(propagation_policy="Foreground"),
                )
            else:
                raise ValueError(f"Unsupported kind: {kind}")
            return True
        except client.exceptions.ApiException as e:
            if e.status == 404:
                return False
            raise

    async def get_service_endpoint(self, namespace: str, service_name: str) -> Optional[str]:
        """Get service endpoint URL"""
        core_v1 = self._get_core_v1()
        try:
            svc = core_v1.read_namespaced_service(
                name=service_name,
                namespace=namespace,
            )
            if svc.spec.type == "LoadBalancer":
                # Wait for external IP
                if not svc.status.load_balancer.ingress:
                    return None
                ip = svc.status.load_balancer.ingress[0].ip
                port = svc.spec.ports[0].port
                return f"http://{ip}:{port}"
            elif svc.spec.type == "ClusterIP":
                port = svc.spec.ports[0].port
                return f"http://{service_name}.{namespace}.svc.cluster.local:{port}"
            return None
        except client.exceptions.ApiException as e:
            if e.status == 404:
                return None
            raise


# Singleton instance
cluster_gateway = ClusterGateway()
