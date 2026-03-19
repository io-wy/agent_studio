"""Training service - business logic for training jobs"""
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    TrainingJob, TrainingJobStatus,
    Model, ModelStatus,
    ModelVersion, ModelVersionStatus,
)
from app.repositories.training import TrainingJobRepository, ModelRepository, ModelVersionRepository
from app.repositories.tenant import ProjectRepository
from app.integrations.kubernetes import cluster_gateway
from app.integrations.object_store import object_store


class TrainingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_repo = TrainingJobRepository(db)
        self.model_repo = ModelRepository(db)
        self.model_version_repo = ModelVersionRepository(db)
        self.project_repo = ProjectRepository(db)

    async def create_training_job(
        self,
        project_id: str,
        name: str,
        base_model: str,
        training_type: str,
        dataset_version_id: Optional[str] = None,
        description: Optional[str] = None,
        config_yaml: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> TrainingJob:
        """Create a new training job"""
        # Verify project exists
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        job = await self.job_repo.create(
            project_id=project_id,
            name=name,
            base_model=base_model,
            training_type=training_type,
            dataset_version_id=dataset_version_id,
            description=description,
            config_yaml=config_yaml,
            created_by=created_by,
        )

        return job

    async def get_job(self, job_id: str) -> Optional[TrainingJob]:
        """Get training job by ID"""
        return await self.job_repo.get(job_id)

    async def list_jobs(self, project_id: str, skip: int = 0, limit: int = 100) -> List[TrainingJob]:
        """List training jobs in project"""
        return await self.job_repo.list_by_project(project_id, skip, limit)

    async def submit_job(self, job_id: str) -> TrainingJob:
        """Submit training job to Kubernetes"""
        job = await self.job_repo.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if job.status != TrainingJobStatus.DRAFT:
            raise ValueError(f"Job {job_id} is not in DRAFT status")

        # Get project for namespace
        project = await self.project_repo.get(job.project_id)

        # Generate K8s job name
        k8s_job_name = f"training-{job.id[:8]}"

        # Build training spec
        spec = self._build_training_spec(job, project.namespace)

        # Create K8s job
        await cluster_gateway.apply_manifest(spec)

        # Update job status
        job = await self.job_repo.update(
            job,
            status=TrainingJobStatus.QUEUED,
            k8s_job_name=k8s_job_name,
            k8s_namespace=project.namespace,
            queued_at=datetime.utcnow(),
        )

        return job

    async def cancel_job(self, job_id: str) -> TrainingJob:
        """Cancel training job"""
        job = await self.job_repo.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if job.status not in [TrainingJobStatus.QUEUED, TrainingJobStatus.RUNNING]:
            raise ValueError(f"Job {job_id} cannot be canceled in {job.status} status")

        # Delete K8s job if running
        if job.k8s_job_name and job.k8s_namespace:
            await cluster_gateway.delete_workload("job", job.k8s_job_name, job.k8s_namespace)

        # Update status
        job = await self.job_repo.update(
            job,
            status=TrainingJobStatus.CANCELED,
            finished_at=datetime.utcnow(),
        )

        return job

    async def sync_job_status(self, job_id: str) -> TrainingJob:
        """Sync job status from Kubernetes"""
        job = await self.job_repo.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if not job.k8s_job_name or not job.k8s_namespace:
            return job

        # Check pod status
        pods = await cluster_gateway.read_pod_status(
            namespace=job.k8s_namespace,
            label_selector=f"job-name={job.k8s_job_name}",
        )

        if not pods:
            return job

        # Determine status from pods
        running_pods = [p for p in pods if p["status"] == "Running"]
        succeeded_pods = [p for p in pods if p["status"] == "Succeeded"]
        failed_pods = [p for p in pods if p["status"] == "Failed"]

        if succeeded_pods:
            job = await self.job_repo.update(
                job,
                status=TrainingJobStatus.SUCCEEDED,
                finished_at=datetime.utcnow(),
            )
            # Create model version
            await self._create_model_from_job(job)
        elif failed_pods:
            job = await self.job_repo.update(
                job,
                status=TrainingJobStatus.FAILED,
                finished_at=datetime.utcnow(),
            )
        elif running_pods:
            # Check if just started
            if job.status == TrainingJobStatus.QUEUED:
                job = await self.job_repo.update(
                    job,
                    status=TrainingJobStatus.RUNNING,
                    started_at=datetime.utcnow(),
                )

        return job

    async def get_job_logs(self, job_id: str, tail_lines: int = 100) -> str:
        """Get training job logs"""
        job = await self.job_repo.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if not job.k8s_job_name or not job.k8s_namespace:
            return "No logs available - job not started"

        # Find the pod
        pods = await cluster_gateway.read_pod_status(
            namespace=job.k8s_namespace,
            label_selector=f"job-name={job.k8s_job_name}",
        )

        if not pods:
            return "No pods found"

        # Get logs from first running/completed pod
        for pod in pods:
            if pod["status"] in ["Running", "Succeeded", "Failed"]:
                logs = await cluster_gateway.read_pod_logs(
                    namespace=job.k8s_namespace,
                    pod_name=pod["name"],
                    tail_lines=tail_lines,
                )
                return logs

        return "No logs available"

    async def get_job_metrics(self, job_id: str) -> Dict[str, Any]:
        """Get training job metrics"""
        job = await self.job_repo.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        metrics = {
            "job_id": job.id,
            "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
            "gpu_hours": job.gpu_hours,
        }

        if job.metrics:
            try:
                metrics["details"] = json.loads(job.metrics)
            except json.JSONDecodeError:
                pass

        return metrics

    def _build_training_spec(self, job: TrainingJob, namespace: str) -> Dict[str, Any]:
        """Build Kubernetes job manifest for training"""
        # Base training image - configurable
        training_image = "ghcr.io/axolotl-ai/axolotl:latest"

        # Build config
        config = {
            "model_dir": "/model",
            "output_dir": "/output",
            "base_model": job.base_model,
            "training_type": job.training_type,
        }

        # Add dataset if available
        if job.dataset_version_id:
            config["dataset_path"] = "/data"

        # Environment variables
        env = [
            {"name": "MODEL_DIR", "value": "/model"},
            {"name": "OUTPUT_DIR", "value": "/output"},
        ]

        # Volume mounts
        volume_mounts = [
            {"name": "model", "mountPath": "/model", "readOnly": True},
            {"name": "output", "mountPath": "/output"},
            {"name": "data", "mountPath": "/data", "readOnly": True},
        ]

        # Volumes
        volumes = [
            {
                "name": "model",
                "emptyDir": {},
            },
            {
                "name": "output",
                "emptyDir": {},
            },
            {
                "name": "data",
                "emptyDir": {},
            },
        ]

        # Build job manifest
        manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": f"training-{job.id[:8]}",
                "namespace": namespace,
                "labels": {
                    "app": "agent-studio",
                    "type": "training",
                    "job-id": job.id,
                },
            },
            "spec": {
                "backoffLimit": 0,
                "ttlSecondsAfterFinished": 3600,
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "agent-studio",
                            "type": "training",
                            "job-id": job.id,
                        },
                    },
                    "spec": {
                        "restartPolicy": "Never",
                        "serviceAccountName": "training-sa",
                        "containers": [
                            {
                                "name": "trainer",
                                "image": training_image,
                                "command": ["python", "-m", "axolotl.cli.train", "/config/axolotl.yml"],
                                "env": env,
                                "volumeMounts": volume_mounts,
                                "resources": {
                                    "requests": {"nvidia.com/gpu": "1", "cpu": "4", "memory": "16Gi"},
                                    "limits": {"nvidia.com/gpu": "1", "cpu": "8", "memory": "32Gi"},
                                },
                            }
                        ],
                        "volumes": volumes,
                    },
                },
            },
        }

        return manifest

    async def _create_model_from_job(self, job: TrainingJob) -> ModelVersion:
        """Create model and version from completed training job"""
        project = await self.project_repo.get(job.project_id)

        # Create model if not exists
        model = await self.model_repo.get(job.model_id) if job.model_id else None

        if not model:
            model = await self.model_repo.create(
                project_id=job.project_id,
                name=f"{job.name}-model",
                base_model=job.base_model,
            )

        # Get next version number
        versions = await self.model_version_repo.list_by_model(model.id)
        next_version = len(versions) + 1

        # Storage prefix
        storage_prefix = f"projects/{job.project_id}/models/{model.id}/versions/v{next_version}"

        # Create model version
        model_version = await self.model_version_repo.create(
            model_id=model.id,
            version=f"v{next_version}",
            storage_prefix=storage_prefix,
            training_job_id=job.id,
            dataset_version_id=job.dataset_version_id,
        )

        # Update training job with model reference
        await self.job_repo.update(job, model_id=model.id)

        # Update model version status
        await self.model_version_repo.update(
            model_version,
            status=ModelVersionStatus.REGISTERED,
        )

        return model_version
