"""Agent service - business logic for agent management"""
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AgentSpec, AgentSpecStatus,
    AgentRevision, AgentRevisionStatus,
    AgentRun, AgentRunStatus,
)
from app.repositories.agent import AgentSpecRepository, AgentRevisionRepository, AgentRunRepository
from app.repositories.tenant import ProjectRepository
from app.integrations.kubernetes import cluster_gateway


class AgentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.spec_repo = AgentSpecRepository(db)
        self.revision_repo = AgentRevisionRepository(db)
        self.run_repo = AgentRunRepository(db)
        self.project_repo = ProjectRepository(db)

    # === AgentSpec ===

    async def create_agent(
        self,
        project_id: str,
        name: str,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[str] = None,
        model_binding: Optional[str] = None,
    ) -> AgentSpec:
        """Create a new agent spec"""
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        spec = await self.spec_repo.create(
            project_id=project_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            tools=tools,
            model_binding=model_binding,
        )
        return spec

    async def get_agent(self, spec_id: str) -> Optional[AgentSpec]:
        """Get agent spec"""
        return await self.spec_repo.get(spec_id)

    async def list_agents(self, project_id: str, skip: int = 0, limit: int = 100) -> List[AgentSpec]:
        """List agents in project"""
        return await self.spec_repo.list_by_project(project_id, skip, limit)

    async def count_agents(self, project_id: str) -> int:
        """Count agents in project"""
        return await self.spec_repo.count_by_project(project_id)

    async def update_agent(self, spec_id: str, **kwargs) -> AgentSpec:
        """Update agent spec"""
        spec = await self.spec_repo.get(spec_id)
        if not spec:
            raise ValueError(f"Agent {spec_id} not found")
        return await self.spec_repo.update(spec, **kwargs)

    # === AgentRevision ===

    async def create_revision(
        self,
        agent_spec_id: str,
        system_prompt: str,
        tools: str,
        model_binding: str,
        workflow_definition: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> AgentRevision:
        """Create new revision from agent spec"""
        spec = await self.spec_repo.get(agent_spec_id)
        if not spec:
            raise ValueError(f"Agent {agent_spec_id} not found")

        # Get latest revision number
        latest = await self.revision_repo.get_latest(agent_spec_id)
        revision_num = (latest.revision + 1) if latest else 1

        # Copy current spec to revision
        revision = await self.revision_repo.create(
            agent_spec_id=agent_spec_id,
            revision=revision_num,
            system_prompt=system_prompt or spec.system_prompt or "",
            tools=tools or spec.tools or "[]",
            model_binding=model_binding or spec.model_binding or "",
            workflow_definition=workflow_definition,
            created_by=created_by,
        )

        return revision

    async def get_revision(self, revision_id: str) -> Optional[AgentRevision]:
        """Get agent revision"""
        return await self.revision_repo.get(revision_id)

    async def list_revisions(self, agent_spec_id: str, skip: int = 0, limit: int = 100) -> List[AgentRevision]:
        """List all revisions of an agent"""
        return await self.revision_repo.list_by_spec(agent_spec_id, skip, limit)

    async def count_revisions(self, agent_spec_id: str) -> int:
        """Count revisions of an agent"""
        return await self.revision_repo.count_by_spec(agent_spec_id)

    async def publish_revision(self, revision_id: str) -> AgentRevision:
        """Publish agent revision"""
        revision = await self.revision_repo.get(revision_id)
        if not revision:
            raise ValueError(f"Revision {revision_id} not found")

        if revision.status != AgentRevisionStatus.APPROVED:
            raise ValueError(f"Revision must be APPROVED before publishing")

        # Update revision status
        revision = await self.revision_repo.update(
            revision,
            status=AgentRevisionStatus.PUBLISHED,
            published_at=datetime.utcnow(),
        )

        # Update agent spec to point to this revision
        await self.spec_repo.update(
            revision.agent_spec_id,
            status=AgentSpecStatus.ACTIVE,
        )

        return revision

    # === AgentRun ===

    async def start_run(
        self,
        revision_id: str,
        input_data: Optional[str] = None,
    ) -> AgentRun:
        """Start a new agent run"""
        revision = await self.revision_repo.get(revision_id)
        if not revision:
            raise ValueError(f"Revision {revision_id} not found")

        if revision.status != AgentRevisionStatus.PUBLISHED:
            raise ValueError("Only PUBLISHED revisions can be run")

        # Create run
        run = await self.run_repo.create(
            revision_id=revision_id,
            input_data=input_data,
        )

        # Get project for namespace
        spec = await self.spec_repo.get(revision.agent_spec_id)
        project = await self.project_repo.get(spec.project_id)

        # Create K8s job for agent runtime
        k8s_job_name = f"agent-run-{run.id[:8]}"
        spec_manifest = self._build_agent_run_spec(run, revision, project.namespace)

        await cluster_gateway.apply_manifest(spec_manifest)

        # Update run
        run = await self.run_repo.update(
            run,
            status=AgentRunStatus.RUNNING,
            k8s_job_name=k8s_job_name,
            k8s_namespace=project.namespace,
            started_at=datetime.utcnow(),
        )

        return run

    async def get_run(self, run_id: str) -> Optional[AgentRun]:
        """Get agent run"""
        return await self.run_repo.get(run_id)

    async def list_runs(self, revision_id: str, skip: int = 0, limit: int = 100) -> List[AgentRun]:
        """List runs for a revision"""
        return await self.run_repo.list_by_revision(revision_id, skip, limit)

    async def count_runs(self, revision_id: str) -> int:
        """Count runs for a revision"""
        return await self.run_repo.count_by_revision(revision_id)

    async def interrupt_run(self, run_id: str, reason: Optional[str] = None) -> AgentRun:
        """Interrupt a running agent"""
        run = await self.run_repo.get(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")

        if run.status not in [AgentRunStatus.RUNNING, AgentRunStatus.WAITING_TOOL, AgentRunStatus.WAITING_HUMAN]:
            raise ValueError(f"Run {run_id} cannot be interrupted in {run.status} status")

        # Delete K8s job
        if run.k8s_job_name and run.k8s_namespace:
            await cluster_gateway.delete_workload("job", run.k8s_job_name, run.k8s_namespace)

        # Update run
        run = await self.run_repo.update(
            run,
            status=AgentRunStatus.ABORTED,
            finished_at=datetime.utcnow(),
            error_message=reason or "Interrupted by user",
        )

        return run

    async def sync_run_status(self, run_id: str) -> AgentRun:
        """Sync run status from Kubernetes"""
        run = await self.run_repo.get(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")

        if not run.k8s_job_name or not run.k8s_namespace:
            return run

        # Check pod status
        pods = await cluster_gateway.read_pod_status(
            namespace=run.k8s_namespace,
            label_selector=f"job-name={run.k8s_job_name}",
        )

        if not pods:
            return run

        # Determine status
        running_pods = [p for p in pods if p["status"] == "Running"]
        succeeded_pods = [p for p in pods if p["status"] == "Succeeded"]
        failed_pods = [p for p in pods if p["status"] == "Failed"]

        if succeeded_pods:
            run = await self.run_repo.update(
                run,
                status=AgentRunStatus.SUCCEEDED,
                finished_at=datetime.utcnow(),
            )
        elif failed_pods:
            run = await self.run_repo.update(
                run,
                status=AgentRunStatus.FAILED,
                finished_at=datetime.utcnow(),
            )

        return run

    def _build_agent_run_spec(self, run: AgentRun, revision: AgentRevision, namespace: str) -> Dict[str, Any]:
        """Build K8s job manifest for agent run"""
        # Agent runtime image - configurable
        agent_image = "ghcr.io/langchainai/langgraph-runtime:latest"

        # Parse tools
        try:
            tools = json.loads(revision.tools) if revision.tools else []
        except json.JSONDecodeError:
            tools = []

        # Prepare environment
        env = [
            {"name": "AGENT_REVISION_ID", "value": revision.id},
            {"name": "AGENT_RUN_ID", "value": run.id},
            {"name": "SYSTEM_PROMPT", "value": revision.system_prompt},
            {"name": "MODEL_BINDING", "value": revision.model_binding},
            {"name": "AGENT_TOOLS", "value": json.dumps(tools)},
            {"name": "INPUT_DATA", "value": run.input_data or "{}"},
        ]

        manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": f"agent-run-{run.id[:8]}",
                "namespace": namespace,
                "labels": {
                    "app": "agent-studio",
                    "type": "agent-run",
                    "run-id": run.id,
                    "revision-id": revision.id,
                },
            },
            "spec": {
                "backoffLimit": 0,
                "ttlSecondsAfterFinished": 3600,
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "agent-studio",
                            "type": "agent-run",
                            "run-id": run.id,
                        },
                    },
                    "spec": {
                        "restartPolicy": "Never",
                        "serviceAccountName": "agent-sa",
                        "containers": [
                            {
                                "name": "agent",
                                "image": agent_image,
                                "command": ["python", "-m", "agent_studio.runtime"],
                                "env": env,
                                "resources": {
                                    "requests": {"cpu": "2", "memory": "4Gi"},
                                    "limits": {"cpu": "4", "memory": "8Gi"},
                                },
                            }
                        ],
                    },
                },
            },
        }

        return manifest
