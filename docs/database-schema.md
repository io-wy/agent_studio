# Agent Studio 数据库 Schema

## 概述

本文档记录 Agent Studio 的数据库表结构，基于架构设计文档第 4 节。

## 关系图

```
tenants (1) ─────< projects (N)
projects (1) ─────< datasets (N)
projects (1) ─────< training_jobs (N)
projects (1) ─────< models (N)
projects (1) ─────< agent_specs (N)
projects (1) ─────< deployments (N)

datasets (1) ─────< dataset_versions (N)
models (1) ─────< model_versions (N)
training_jobs (1) ─────< model_versions (N)
agent_specs (1) ─────< agent_revisions (N)
agent_revisions (1) ─────< agent_runs (N)
agent_revisions (1) ─────< deployments (N)
model_versions (1) ─────< deployments (N)
```

## 表结构

### 1. tenants (租户)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| name | VARCHAR(255) | UNIQUE, INDEX | 租户名称 |
| status | ENUM | DEFAULT 'active' | active, suspended, deleted |
| quota_gpuHours | INT | DEFAULT 1000 | GPU 小时配额 |
| quota_storage_gb | INT | DEFAULT 100 | 存储配额(GB) |
| quota_deployments | INT | DEFAULT 5 | 最大部署数 |
| created_at | TIMESTAMP | | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

### 2. projects (项目)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| tenant_id | VARCHAR(36) | FK → tenants.id | 所属租户 |
| name | VARCHAR(255) | INDEX | 项目名称 |
| description | TEXT | NULLABLE | 项目描述 |
| status | ENUM | DEFAULT 'active' | active, suspended, deleted |
| namespace | VARCHAR(253) | UNIQUE | K8s namespace |
| quota_gpuHours | INT | DEFAULT 100 | 项目级GPU配额 |
| quota_storage_gb | INT | DEFAULT 10 | 项目级存储配额 |
| quota_deployments | INT | DEFAULT 2 | 项目级部署配额 |
| created_at | TIMESTAMP | | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

### 3. datasets (数据集)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| project_id | VARCHAR(36) | FK → projects.id, INDEX | 所属项目 |
| name | VARCHAR(255) | INDEX | 数据集名称 |
| description | TEXT | NULLABLE | 描述 |
| status | ENUM | DEFAULT 'draft' | draft, active, archived |
| data_format | VARCHAR(50) | | jsonl, parquet, csv, json |
| schema | TEXT | NULLABLE | JSON Schema |
| storage_prefix | VARCHAR(500) | | S3 存储路径 |
| created_at | TIMESTAMP | | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

### 4. dataset_versions (数据集版本)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| dataset_id | VARCHAR(36) | FK → datasets.id, INDEX | 所属数据集 |
| version | VARCHAR(50) | | 版本号(v1, v2...) |
| description | TEXT | NULLABLE | 版本描述 |
| status | ENUM | DEFAULT 'created' | created, validating, validated, failed |
| storage_prefix | VARCHAR(500) | | 版本存储路径 |
| row_count | INT | NULLABLE | 行数 |
| file_size_bytes | INT | NULLABLE | 文件大小 |
| checksum | VARCHAR(64) | NULLABLE | SHA256 |
| lakefs_commit | VARCHAR(100) | NULLABLE | lakeFS commit hash |
| validation_errors | TEXT | NULLABLE | 验证错误(JSON) |
| created_at | TIMESTAMP | | 创建时间 |
| created_by | VARCHAR(36) | NULLABLE | 创建者 |

### 5. models (模型)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| project_id | VARCHAR(36) | FK → projects.id, INDEX | 所属项目 |
| name | VARCHAR(255) | INDEX | 模型名称 |
| description | TEXT | NULLABLE | 模型描述 |
| status | ENUM | DEFAULT 'draft' | draft, active, archived |
| base_model | VARCHAR(255) | | 基础模型 |
| created_at | TIMESTAMP | | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

### 6. model_versions (模型版本)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| model_id | VARCHAR(36) | FK → models.id, INDEX | 所属模型 |
| version | VARCHAR(50) | | 版本号 |
| status | ENUM | DEFAULT 'registered' | registered, validated, staged, production, deprecated |
| storage_prefix | VARCHAR(500) | | 模型文件路径 |
| mlflow_run_id | VARCHAR(36) | NULLABLE | MLflow Run ID |
| mlflow_model_uri | VARCHAR(500) | NULLABLE | MLflow Model URI |
| training_metrics | TEXT | NULLABLE | 训练指标(JSON) |
| dataset_version_id | VARCHAR(36) | FK → dataset_versions.id | 训练数据集 |
| training_job_id | VARCHAR(36) | FK → training_jobs.id | 来源训练任务 |
| created_at | TIMESTAMP | | 创建时间 |
| created_by | VARCHAR(36) | NULLABLE | 创建者 |

### 7. training_jobs (训练任务)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| project_id | VARCHAR(36) | FK → projects.id, INDEX | 所属项目 |
| dataset_version_id | VARCHAR(36) | FK → dataset_versions.id | 训练数据集 |
| model_id | VARCHAR(36) | FK → models.id | 目标模型 |
| name | VARCHAR(255) | | 任务名称 |
| description | TEXT | NULLABLE | 任务描述 |
| status | ENUM | DEFAULT 'draft' | draft, queued, admitted, running, succeeded, failed, canceled |
| base_model | VARCHAR(255) | | 基础模型 |
| training_type | VARCHAR(50) | | lora, qlora, full |
| config_yaml | TEXT | NULLABLE | Axolotl 配置 |
| k8s_job_name | VARCHAR(253) | NULLABLE | K8s Job 名称 |
| k8s_namespace | VARCHAR(253) | NULLABLE | K8s Namespace |
| gpu_hours | FLOAT | NULLABLE | GPU 使用小时 |
| metrics | TEXT | NULLABLE | 训练指标(JSON) |
| queued_at | TIMESTAMP | NULLABLE | 入队时间 |
| started_at | TIMESTAMP | NULLABLE | 开始时间 |
| finished_at | TIMESTAMP | NULLABLE | 结束时间 |
| created_at | TIMESTAMP | | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |
| created_by | VARCHAR(36) | NULLABLE | 创建者 |

### 8. agent_specs (Agent 规范)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| project_id | VARCHAR(36) | FK → projects.id, INDEX | 所属项目 |
| name | VARCHAR(255) | INDEX | Agent 名称 |
| description | TEXT | NULLABLE | Agent 描述 |
| status | ENUM | DEFAULT 'draft' | draft, active, archived |
| system_prompt | TEXT | NULLABLE | 系统提示词 |
| tools | TEXT | NULLABLE | 工具定义(JSON) |
| model_binding | VARCHAR(255) | NULLABLE | 绑定的模型 |
| created_at | TIMESTAMP | | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

### 9. agent_revisions (Agent 版本)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| agent_spec_id | VARCHAR(36) | FK → agent_specs.id, INDEX | 所属规范 |
| revision | INT | | 版本号 |
| status | ENUM | DEFAULT 'draft' | draft, tested, approved, published, deprecated |
| system_prompt | TEXT | | 完整快照 |
| tools | TEXT | | 工具定义(JSON) |
| model_binding | VARCHAR(255) | | 模型绑定 |
| workflow_definition | TEXT | NULLABLE | LangGraph 定义 |
| bundle_path | VARCHAR(500) | NULLABLE | Bundle 路径 |
| eval_score | FLOAT | NULLABLE | 评估分数 |
| eval_report | TEXT | NULLABLE | 评估报告 |
| created_at | TIMESTAMP | | 创建时间 |
| created_by | VARCHAR(36) | NULLABLE | 创建者 |
| published_at | TIMESTAMP | NULLABLE | 发布时间 |

### 10. agent_runs (Agent 运行)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| revision_id | VARCHAR(36) | FK → agent_revisions.id, INDEX | 运行的版本 |
| status | ENUM | DEFAULT 'queued' | queued, running, waiting_tool, waiting_human, succeeded, failed, aborted |
| input_data | TEXT | NULLABLE | 输入数据(JSON) |
| k8s_job_name | VARCHAR(253) | NULLABLE | K8s Job 名称 |
| k8s_namespace | VARCHAR(253) | NULLABLE | K8s Namespace |
| output_data | TEXT | NULLABLE | 输出数据(JSON) |
| error_message | TEXT | NULLABLE | 错误信息 |
| tokens_used | INT | NULLABLE | 使用 token 数 |
| tool_calls | INT | NULLABLE | 工具调用次数 |
| duration_seconds | INT | NULLABLE | 运行时间(秒) |
| started_at | TIMESTAMP | NULLABLE | 开始时间 |
| finished_at | TIMESTAMP | NULLABLE | 结束时间 |
| created_at | TIMESTAMP | | 创建时间 |

### 11. deployments (部署)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| project_id | VARCHAR(36) | FK → projects.id, INDEX | 所属项目 |
| model_version_id | VARCHAR(36) | FK → model_versions.id | 部署的模型版本 |
| agent_revision_id | VARCHAR(36) | FK → agent_revisions.id | 部署的 Agent 版本 |
| name | VARCHAR(255) | | 部署名称 |
| description | TEXT | NULLABLE | 部署描述 |
| status | ENUM | DEFAULT 'pending' | pending, provisioning, ready, scaling, degraded, failed, deleting |
| deployment_type | VARCHAR(50) | | kserve, ray |
| model_format | VARCHAR(50) | NULLABLE | pytorch, vllm, triton |
| replicas | INT | DEFAULT 1 | 副本数 |
| min_replicas | INT | DEFAULT 0 | 最小副本 |
| max_replicas | INT | DEFAULT 3 | 最大副本 |
| gpu_count | INT | DEFAULT 1 | GPU 数量 |
| endpoint_url | VARCHAR(500) | NULLABLE | 推理端点 |
| service_url | VARCHAR(500) | NULLABLE | 服务地址 |
| k8s_service_name | VARCHAR(253) | NULLABLE | K8s Service |
| k8s_ingress_name | VARCHAR(253) | NULLABLE | K8s Ingress |
| traffic_percentage | INT | DEFAULT 100 | 流量权重 |
| metrics | TEXT | NULLABLE | 指标(JSON) |
| created_at | TIMESTAMP | | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |
| ready_at | TIMESTAMP | NULLABLE | 就绪时间 |
| created_by | VARCHAR(36) | NULLABLE | 创建者 |

### 12. audit_events (审计事件)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| actor_id | VARCHAR(36) | NULLABLE | 操作者 ID |
| actor_type | VARCHAR(50) | NULLABLE | user, system, service |
| tenant_id | VARCHAR(36) | NULLABLE, INDEX | 租户 ID |
| project_id | VARCHAR(36) | NULLABLE, INDEX | 项目 ID |
| resource_type | VARCHAR(50) | | 资源类型 |
| resource_id | VARCHAR(36) | | 资源 ID |
| action | VARCHAR(100) | | 操作类型 |
| before_state | JSON | NULLABLE | 操作前状态 |
| after_state | JSON | NULLABLE | 操作后状态 |
| request_id | VARCHAR(36) | NULLABLE | 请求 ID |
| ip_address | VARCHAR(45) | NULLABLE | IP 地址 |
| user_agent | VARCHAR(500) | NULLABLE | 用户代理 |
| description | TEXT | NULLABLE | 描述 |
| created_at | TIMESTAMP | INDEX | 创建时间 |

### 13. operations (操作)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| name | VARCHAR(255) | | 操作名称 |
| operation_type | VARCHAR(50) | | 操作类型 |
| status | ENUM | DEFAULT 'pending' | pending, running, succeeded, failed, canceled |
| resource_type | VARCHAR(50) | NULLABLE | 资源类型 |
| resource_id | VARCHAR(36) | NULLABLE | 资源 ID |
| request | JSON | NULLABLE | 请求数据 |
| response | JSON | NULLABLE | 响应数据 |
| progress | INT | DEFAULT 0 | 进度(0-100) |
| message | TEXT | NULLABLE | 消息 |
| started_at | TIMESTAMP | NULLABLE | 开始时间 |
| finished_at | TIMESTAMP | NULLABLE | 结束时间 |
| created_at | TIMESTAMP | | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |
| created_by | VARCHAR(36) | NULLABLE | 创建者 |

### 14. events (事件)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(36) | PK | UUID |
| event_type | VARCHAR(100) | | 事件类型 |
| tenant_id | VARCHAR(36) | NULLABLE, INDEX | 租户 ID |
| project_id | VARCHAR(36) | NULLABLE, INDEX | 项目 ID |
| resource_type | VARCHAR(50) | NULLABLE | 资源类型 |
| resource_id | VARCHAR(36) | NULLABLE | 资源 ID |
| payload | JSON | NULLABLE | 事件载荷 |
| created_at | TIMESTAMP | INDEX | 创建时间 |

## 索引

| 表 | 索引字段 |
|----|----------|
| tenants | name (UNIQUE) |
| projects | tenant_id, name, namespace (UNIQUE) |
| datasets | project_id, name |
| dataset_versions | dataset_id |
| models | project_id, name |
| model_versions | model_id |
| training_jobs | project_id |
| agent_specs | project_id, name |
| agent_revisions | agent_spec_id |
| agent_runs | revision_id |
| deployments | project_id |
| audit_events | tenant_id, project_id, created_at |
| events | tenant_id, project_id, created_at |

## 迁移

使用 Alembic 进行数据库迁移：

```bash
# 安装依赖
cd backend
pip install alembic

# 运行迁移
alembic upgrade head

# 创建新迁移
alembic revision --autogenerate -m "add new field"

# 回滚
alembic downgrade -1
```

迁移文件位置：`backend/alembic/versions/`
