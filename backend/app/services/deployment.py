"""Deployment service - business logic for model/agent deployment"""
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Deployment, DeploymentStatus, ModelVersion, AgentRevision
from app.repositories.deployment import DeploymentRepository
from app.repositories.tenant import ProjectRepository
from app.repositories.training import ModelVersionRepository
from app.repositories.agent import AgentRevisionRepository
from app.integrations.kubernetes import cluster_gateway


class DeploymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.deployment_repo = DeploymentRepository(db)
        self.project_repo = ProjectRepository(db)
        self.model_version_repo = ModelVersionRepository(db)
        self.revision_repo = AgentRevisionRepository(db)

    async def create_deployment(
        self,
        project_id: str,
        name: str,
        deployment_type: str,
        model_version_id: Optional[str] = None,
        agent_revision_id: Optional[str] = None,
        description: Optional[str] = None,
        model_format: Optional[str] = None,
        replicas: int = 1,
        min_replicas: int = 0,
        max_replicas: int = 3,
        gpu_count: int = 1,
        created_by: Optional[str] = None,
    ) -> Deployment:
        """Create a new deployment"""
        # Verify project exists
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Verify model version or agent revision exists
        if model_version_id:
            model_version = await self.model_version_repo.get(model_version_id)
            if not model_version:
                raise ValueError(f"Model version {model_version_id} not found")
        elif agent_revision_id:
            revision = await self.revision_repo.get(agent_revision_id)
            if not revision:
                raise ValueError(f"Agent revision {agent_revision_id} not found")
        else:
            raise ValueError("Either model_version_id or agent_revision_id must be provided")

        deployment = await self.deployment_repo.create(
            project_id=project_id,
            name=name,
            deployment_type=deployment_type,
            model_version_id=model_version_id,
            agent_revision_id=agent_revision_id,
            description=description,
            model_format=model_format,
            replicas=replicas,
            min_replicas=min_replicas,
            max_replicas=max_replicas,
            gpu_count=gpu_count,
            created_by=created_by,
        )

        return deployment

    async def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Get deployment by ID"""
        return await self.deployment_repo.get(deployment_id)

    async def list_deployments(self, project_id: str, skip: int = 0, limit: int = 100) -> List[Deployment]:
        """List deployments in project"""
        return await self.deployment_repo.list_by_project(project_id, skip, limit)

    async def deploy(self, deployment_id: str) -> Deployment:
        """Deploy to Kubernetes"""
        deployment = await self.deployment_repo.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        if deployment.status != DeploymentStatus.PENDING:
            raise ValueError(f"Deployment {deployment_id} is not in PENDING status")

        project = await self.project_repo.get(deployment.project_id)

        # Build deployment manifest based on type
        if deployment.deployment_type == "kserve":
            manifest = self._build_kserve_manifest(deployment, project.namespace)
        elif deployment.deployment_type == "ray":
            manifest = self._build_ray_manifest(deployment, project.namespace)
        else:
            raise ValueError(f"Unsupported deployment type: {deployment.deployment_type}")

        # Apply manifest
        await cluster_gateway.apply_manifest(manifest)

        # Update status
        deployment = await self.deployment_repo.update(
            deployment,
            status=DeploymentStatus.PROVISIONING,
            k8s_service_name=f"{deployment.name}-svc",
        )

        return deployment

    async def scale_deployment(
        self,
        deployment_id: str,
        replicas: Optional[int] = None,
        min_replicas: Optional[int] = None,
        max_replicas: Optional[int] = None,
    ) -> Deployment:
        """Scale deployment"""
        deployment = await self.deployment_repo.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        if deployment.status not in [DeploymentStatus.READY, DeploymentStatus.SCALING]:
            raise ValueError(f"Cannot scale deployment in {deployment.status} status")

        update_data = {}
        if replicas is not None:
            update_data["replicas"] = replicas
        if min_replicas is not None:
            update_data["min_replicas"] = min_replicas
        if max_replicas is not None:
            update_data["max_replicas"] = max_replicas

        deployment = await self.deployment_repo.update(deployment, **update_data)

        # TODO: Actually scale the K8s deployment

        return deployment

    async def traffic_shift(
        self,
        deployment_id: str,
        target_revision_id: Optional[str] = None,
        target_percentage: int = 100,
    ) -> Deployment:
        """Shift traffic between revisions"""
        deployment = await self.deployment_repo.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        if deployment.status != DeploymentStatus.READY:
            raise ValueError(f"Deployment must be READY for traffic shift")

        # Update traffic percentage
        deployment = await self.deployment_repo.update(
            deployment,
            traffic_percentage=target_percentage,
        )

        # TODO: Update Ingress to shift traffic

        return deployment

    async def rollback_deployment(
        self,
        deployment_id: str,
        revision_id: Optional[str] = None,
    ) -> Deployment:
        """Rollback to previous revision"""
        deployment = await self.deployment_repo.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        # TODO: Implement rollback logic
        # For now, just update traffic back to 100%

        deployment = await self.deployment_repo.update(
            deployment,
            traffic_percentage=100,
        )

        return deployment

    async def delete_deployment(self, deployment_id: str) -> bool:
        """Delete deployment"""
        deployment = await self.deployment_repo.get(deployment_id)
        if not deployment:
            return False

        # Delete K8s resources
        if deployment.k8s_service_name:
            await cluster_gateway.delete_workload(
                "service",
                deployment.k8s_service_name,
                deployment.project_id,
            )

        # Delete from database
        await self.deployment_repo.delete(deployment)
        return True

    async def get_health(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment health status"""
        deployment = await self.deployment_repo.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        # TODO: Actually query K8s for real health data
        # For now, return basic info

        return {
            "deployment_id": deployment.id,
            "status": deployment.status.value if hasattr(deployment.status, 'value') else str(deployment.status),
            "replicas_ready": deployment.replicas,
            "replicas_total": deployment.replicas,
            "gpu_utilization": None,
            "avg_latency_ms": None,
            "last_check": datetime.utcnow().isoformat(),
        }

    async def sync_deployment_status(self, deployment_id: str) -> Deployment:
        """Sync deployment status from Kubernetes"""
        deployment = await self.deployment_repo.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        # TODO: Query K8s for actual status
        # For now, assume PROVISIONING -> READY after some time

        if deployment.status == DeploymentStatus.PROVISIONING:
            # Check if service is ready
            if deployment.k8s_service_name:
                endpoint = await cluster_gateway.get_service_endpoint(
                    namespace=deployment.project_id,
                    service_name=deployment.k8s_service_name,
                )
                if endpoint:
                    deployment = await self.deployment_repo.update(
                        deployment,
                        status=DeploymentStatus.READY,
                        endpoint_url=endpoint,
                        service_url=endpoint,
                        ready_at=datetime.utcnow(),
                    )

        return deployment

    def _build_kserve_manifest(self, deployment: Deployment, namespace: str) -> Dict[str, Any]:
        """Build KServe InferenceService manifest"""
        # Determine model format and image
        if deployment.model_format == "vllm":
            inference_image = "ghcr.io/vllm/vllm-openai:latest"
        elif deployment.model_format == "pytorch":
            inference_image = "pytorch/torchserve:latest"
        elif deployment.model_format == "triton":
            inference_image = "nvcr.io/nvidia/tritonserver:latest"
        else:
            inference_image = "pytorch/torchserve:latest"

        # Get model storage path
        storage_uri = f"s3://{deployment.model_version_id}"  # Simplified

        # Build InferenceService manifest
        manifest = {
            "apiVersion": "serving.kserve.io/v1beta1",
            "kind": "InferenceService",
            "metadata": {
                "name": deployment.name,
                "namespace": namespace,
                "labels": {
                    "app": "agent-studio",
                    "deployment-id": deployment.id,
                },
            },
            "spec": {
                "predictor": {
                    "model": {
                        "modelFormat": {
                            "name": deployment.model_format or "pytorch",
                        },
                        "storageUri": storage_uri,
                        "resources": {
                            "limits": {
                                "nvidia.com/gpu": str(deployment.gpu_count),
                                "cpu": "4",
                                "memory": "16Gi",
                            },
                            "requests": {
                                "cpu": "2",
                                "memory": "8Gi",
                            },
                        },
                    },
                },
                "autoscaler": {
                    "minReplicas": deployment.min_replicas,
                    "maxReplicas": deployment.max_replicas,
                    "targetUtilizationPercentage": 70,
                },
            },
        }

        return manifest

    def _build_ray_manifest(self, deployment: Deployment, namespace: str) -> Dict[str, Any]:
        """Build Ray Serve deployment manifest"""
        # Ray Serve config
        config = {
            "deployment_name": deployment.name,
            "num_replicas": deployment.replicas,
            "ray_actor_options": {
                "num_cpus": 2,
                "num_gpus": deployment.gpu_count,
            },
        }

        manifest = {
            "apiVersion": "ray.io/v1alpha1",
            "kind": "RayService",
            "metadata": {
                "name": deployment.name,
                "namespace": namespace,
                "labels": {
                    "app": "agent-studio",
                    "deployment-id": deployment.id,
                },
            },
            "spec": {
                "serviceUnhealthySecondThreshold": 60,
                "serviceHealthCheckSecond": 5,
                "rayStartParams": {
                    "dashboard-host": "0.0.0.0",
                    "num-gpus": str(deployment.gpu_count),
                },
                "serveConfigs": json.dumps(config),
                "runtimeEnvYAML": """
env_vars:
  RAY_SERVE_ENABLE_EXTERNAL_NAMESPACE: "true"
""",
            },
        }

        return manifest
