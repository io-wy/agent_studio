"""Initial migration - create all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-03-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =====================
    # Tenant & Project
    # =====================
    op.create_table(
        'tenants',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('name', String(255), nullable=False, unique=True, index=True),
        sa.Column('status', SQLEnum('active', 'suspended', 'deleted', name='tenantstatus'), nullable=False, server_default='active'),
        sa.Column('quota_gpuHours', Integer, nullable=False, server_default='1000'),
        sa.Column('quota_storage_gb', Integer, nullable=False, server_default='100'),
        sa.Column('quota_deployments', Integer, nullable=False, server_default='5'),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'projects',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('tenant_id', String(36), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('name', String(255), nullable=False, index=True),
        sa.Column('description', Text, nullable=True),
        sa.Column('status', SQLEnum('active', 'suspended', 'deleted', name='projectstatus'), nullable=False, server_default='active'),
        sa.Column('namespace', String(253), nullable=False, unique=True),
        sa.Column('quota_gpuHours', Integer, nullable=False, server_default='100'),
        sa.Column('quota_storage_gb', Integer, nullable=False, server_default='10'),
        sa.Column('quota_deployments', Integer, nullable=False, server_default='2'),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # =====================
    # Dataset & Version
    # =====================
    op.create_table(
        'datasets',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('project_id', String(36), sa.ForeignKey('projects.id'), nullable=False, index=True),
        sa.Column('name', String(255), nullable=False, index=True),
        sa.Column('description', Text, nullable=True),
        sa.Column('status', SQLEnum('draft', 'active', 'archived', name='datasetstatus'), nullable=False, server_default='draft'),
        sa.Column('data_format', String(50), nullable=False),
        sa.Column('schema', Text, nullable=True),
        sa.Column('storage_prefix', String(500), nullable=False),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'dataset_versions',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('dataset_id', String(36), sa.ForeignKey('datasets.id'), nullable=False, index=True),
        sa.Column('version', String(50), nullable=False),
        sa.Column('description', Text, nullable=True),
        sa.Column('status', SQLEnum('created', 'validating', 'validated', 'failed', name='datasetversionstatus'), nullable=False, server_default='created'),
        sa.Column('storage_prefix', String(500), nullable=False),
        sa.Column('row_count', Integer, nullable=True),
        sa.Column('file_size_bytes', Integer, nullable=True),
        sa.Column('checksum', String(64), nullable=True),
        sa.Column('lakefs_commit', String(100), nullable=True),
        sa.Column('validation_errors', Text, nullable=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', String(36), nullable=True),
    )

    # =====================
    # Model & Training
    # =====================
    op.create_table(
        'models',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('project_id', String(36), sa.ForeignKey('projects.id'), nullable=False, index=True),
        sa.Column('name', String(255), nullable=False, index=True),
        sa.Column('description', Text, nullable=True),
        sa.Column('status', SQLEnum('draft', 'active', 'archived', name='modelstatus'), nullable=False, server_default='draft'),
        sa.Column('base_model', String(255), nullable=False),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'model_versions',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('model_id', String(36), sa.ForeignKey('models.id'), nullable=False, index=True),
        sa.Column('version', String(50), nullable=False),
        sa.Column('status', SQLEnum('registered', 'validated', 'staged', 'production', 'deprecated', name='modelversionstatus'), nullable=False, server_default='registered'),
        sa.Column('storage_prefix', String(500), nullable=False),
        sa.Column('mlflow_run_id', String(36), nullable=True),
        sa.Column('mlflow_model_uri', String(500), nullable=True),
        sa.Column('training_metrics', Text, nullable=True),
        sa.Column('dataset_version_id', String(36), sa.ForeignKey('dataset_versions.id'), nullable=True),
        sa.Column('training_job_id', String(36), sa.ForeignKey('training_jobs.id'), nullable=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', String(36), nullable=True),
    )

    op.create_table(
        'training_jobs',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('project_id', String(36), sa.ForeignKey('projects.id'), nullable=False, index=True),
        sa.Column('dataset_version_id', String(36), sa.ForeignKey('dataset_versions.id'), nullable=True),
        sa.Column('model_id', String(36), sa.ForeignKey('models.id'), nullable=True),
        sa.Column('name', String(255), nullable=False),
        sa.Column('description', Text, nullable=True),
        sa.Column('status', SQLEnum('draft', 'queued', 'admitted', 'running', 'succeeded', 'failed', 'canceled', name='trainingjobstatus'), nullable=False, server_default='draft'),
        sa.Column('base_model', String(255), nullable=False),
        sa.Column('training_type', String(50), nullable=False),
        sa.Column('config_yaml', Text, nullable=True),
        sa.Column('k8s_job_name', String(253), nullable=True),
        sa.Column('k8s_namespace', String(253), nullable=True),
        sa.Column('gpu_hours', Float, nullable=True),
        sa.Column('metrics', Text, nullable=True),
        sa.Column('queued_at', DateTime, nullable=True),
        sa.Column('started_at', DateTime, nullable=True),
        sa.Column('finished_at', DateTime, nullable=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', String(36), nullable=True),
    )

    # =====================
    # Agent & Deployment
    # =====================
    op.create_table(
        'agent_specs',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('project_id', String(36), sa.ForeignKey('projects.id'), nullable=False, index=True),
        sa.Column('name', String(255), nullable=False, index=True),
        sa.Column('description', Text, nullable=True),
        sa.Column('status', SQLEnum('draft', 'active', 'archived', name='agentspecstatus'), nullable=False, server_default='draft'),
        sa.Column('system_prompt', Text, nullable=True),
        sa.Column('tools', Text, nullable=True),
        sa.Column('model_binding', String(255), nullable=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'agent_revisions',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('agent_spec_id', String(36), sa.ForeignKey('agent_specs.id'), nullable=False, index=True),
        sa.Column('revision', Integer, nullable=False),
        sa.Column('status', SQLEnum('draft', 'tested', 'approved', 'published', 'deprecated', name='agentrevisionstatus'), nullable=False, server_default='draft'),
        sa.Column('system_prompt', Text, nullable=False),
        sa.Column('tools', Text, nullable=False),
        sa.Column('model_binding', String(255), nullable=False),
        sa.Column('workflow_definition', Text, nullable=True),
        sa.Column('bundle_path', String(500), nullable=True),
        sa.Column('eval_score', Float, nullable=True),
        sa.Column('eval_report', Text, nullable=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', String(36), nullable=True),
        sa.Column('published_at', DateTime, nullable=True),
    )

    op.create_table(
        'agent_runs',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('revision_id', String(36), sa.ForeignKey('agent_revisions.id'), nullable=False, index=True),
        sa.Column('status', SQLEnum('queued', 'running', 'waiting_tool', 'waiting_human', 'succeeded', 'failed', 'aborted', name='agentrunstatus'), nullable=False, server_default='queued'),
        sa.Column('input_data', Text, nullable=True),
        sa.Column('k8s_job_name', String(253), nullable=True),
        sa.Column('k8s_namespace', String(253), nullable=True),
        sa.Column('output_data', Text, nullable=True),
        sa.Column('error_message', Text, nullable=True),
        sa.Column('tokens_used', Integer, nullable=True),
        sa.Column('tool_calls', Integer, nullable=True),
        sa.Column('duration_seconds', Integer, nullable=True),
        sa.Column('started_at', DateTime, nullable=True),
        sa.Column('finished_at', DateTime, nullable=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'deployments',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('project_id', String(36), sa.ForeignKey('projects.id'), nullable=False, index=True),
        sa.Column('model_version_id', String(36), sa.ForeignKey('model_versions.id'), nullable=True),
        sa.Column('agent_revision_id', String(36), sa.ForeignKey('agent_revisions.id'), nullable=True),
        sa.Column('name', String(255), nullable=False),
        sa.Column('description', Text, nullable=True),
        sa.Column('status', SQLEnum('pending', 'provisioning', 'ready', 'scaling', 'degraded', 'failed', 'deleting', name='deploymentstatus'), nullable=False, server_default='pending'),
        sa.Column('deployment_type', String(50), nullable=False),
        sa.Column('model_format', String(50), nullable=True),
        sa.Column('replicas', Integer, nullable=False, server_default='1'),
        sa.Column('min_replicas', Integer, nullable=False, server_default='0'),
        sa.Column('max_replicas', Integer, nullable=False, server_default='3'),
        sa.Column('gpu_count', Integer, nullable=False, server_default='1'),
        sa.Column('endpoint_url', String(500), nullable=True),
        sa.Column('service_url', String(500), nullable=True),
        sa.Column('k8s_service_name', String(253), nullable=True),
        sa.Column('k8s_ingress_name', String(253), nullable=True),
        sa.Column('traffic_percentage', Integer, nullable=False, server_default='100'),
        sa.Column('metrics', Text, nullable=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('ready_at', DateTime, nullable=True),
        sa.Column('created_by', String(36), nullable=True),
    )

    # =====================
    # Audit & Events
    # =====================
    op.create_table(
        'audit_events',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('actor_id', String(36), nullable=True),
        sa.Column('actor_type', String(50), nullable=True),
        sa.Column('tenant_id', String(36), nullable=True, index=True),
        sa.Column('project_id', String(36), nullable=True, index=True),
        sa.Column('resource_type', String(50), nullable=False),
        sa.Column('resource_id', String(36), nullable=False),
        sa.Column('action', String(100), nullable=False),
        sa.Column('before_state', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('after_state', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('request_id', String(36), nullable=True),
        sa.Column('ip_address', String(45), nullable=True),
        sa.Column('user_agent', String(500), nullable=True),
        sa.Column('description', Text, nullable=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now(), index=True),
    )

    op.create_table(
        'operations',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('name', String(255), nullable=False),
        sa.Column('operation_type', String(50), nullable=False),
        sa.Column('status', SQLEnum('pending', 'running', 'succeeded', 'failed', 'canceled', name='operationstatus'), nullable=False, server_default='pending'),
        sa.Column('resource_type', String(50), nullable=True),
        sa.Column('resource_id', String(36), nullable=True),
        sa.Column('request', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('response', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('progress', Integer, nullable=False, server_default='0'),
        sa.Column('message', Text, nullable=True),
        sa.Column('started_at', DateTime, nullable=True),
        sa.Column('finished_at', DateTime, nullable=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', String(36), nullable=True),
    )

    op.create_table(
        'events',
        sa.Column('id', String(36), primary_key=True),
        sa.Column('event_type', String(100), nullable=False),
        sa.Column('tenant_id', String(36), nullable=True, index=True),
        sa.Column('project_id', String(36), nullable=True, index=True),
        sa.Column('resource_type', String(50), nullable=True),
        sa.Column('resource_id', String(36), nullable=True),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', DateTime, nullable=False, server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table('events')
    op.drop_table('operations')
    op.drop_table('audit_events')
    op.drop_table('deployments')
    op.drop_table('agent_runs')
    op.drop_table('agent_revisions')
    op.drop_table('agent_specs')
    op.drop_table('training_jobs')
    op.drop_table('model_versions')
    op.drop_table('models')
    op.drop_table('dataset_versions')
    op.drop_table('datasets')
    op.drop_table('projects')
    op.drop_table('tenants')
