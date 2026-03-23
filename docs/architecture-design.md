# Agent Studio 架构设计

## 1. 系统概述

Agent Studio 是一个多租户 AI Agent 编排与管理平台，提供从数据管理、模型训练、Agent 开发到部署运行的全链路能力。

**核心能力**：
- 多租户隔离与资源配额管理
- 数据集版本化与存储
- 训练任务提交与模型注册
- Agent 规范定义与版本发布
- 模型部署与流量管理
- 实时日志与事件流

---

## 2. 技术架构

### 2.1 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| API 控制面 | FastAPI + Pydantic + SQLAlchemy | 统一 REST / WebSocket API |
| 元数据数据库 | PostgreSQL 16 | 业务主存储 |
| 缓存与事件分发 | Redis 7 | 状态缓存、事件广播 |
| 对象存储 | MinIO / S3 | 数据集、checkpoint、模型工件、日志 |
| 数据版本化 | lakeFS | 数据 commit / branch / merge / rollback |
| 模型注册 | MLflow | 实验跟踪、模型版本、Model Registry |
| GPU 作业调度 | Kubernetes + Kueue | 批作业调度与配额控制 |
| 推理部署 | KServe + vLLM | OpenAI-compatible serving |
| Agent Runtime | LangGraph | durable execution、streaming、HITL |

### 2.2 部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         负载均衡 / Ingress                       │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                      FastAPI Backend (API Server)               │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐   │
│  │   Tenant     │   Dataset    │   Training   │   Agent      │   │
│  │   Router     │   Router     │   Router     │   Router     │   │
│  └──────────────┴──────────────┴──────────────┴──────────────┘   │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐   │
│  │  Deployment  │   Events    │    Log       │   Security   │   │
│  │   Router     │   Router     │   Router     │   Middleware │   │
│  └──────────────┴──────────────┴──────────────┴──────────────┘   │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  PostgreSQL   │      │     Redis    │      │    MinIO      │
│   (Metadata) │      │ (Cache/Event) │      │ (Object Store)│
└───────────────┘      └───────────────┘      └───────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│    lakeFS     │      │    MLflow     │      │  Kubernetes   │
│ (Data Version)│      │(Model Registry)      │ (Training/Deploy)│
└───────────────┘      └───────────────┘      └───────────────┘
```

---

## 3. 模块划分

### 3.1 目录结构

```
backend/
└── app/
    ├── api/v1/
    │   └── endpoints/      # API 路由层
    │       ├── tenant.py   # 租户管理
    │       ├── dataset.py  # 数据集管理
    │       ├── training.py # 训练与模型
    │       ├── agent.py    # Agent管理
    │       ├── deployment.py # 部署管理
    │       ├── events.py   # 事件流 (WebSocket/SSE)
    │       └── log.py      # 日志查询
    ├── core/               # 核心配置
    │   ├── config.py       # 环境配置
    │   └── database.py     # 数据库连接
    ├── models/             # SQLAlchemy 实体
    │   ├── tenant.py
    │   ├── dataset.py
    │   ├── training.py
    │   ├── agent.py
    │   └── audit.py
    ├── schemas/            # Pydantic DTO
    │   ├── tenant.py
    │   ├── dataset.py
    │   ├── training.py
    │   └── agent.py
    ├── repositories/       # 数据访问层
    │   ├── tenant.py
    │   ├── dataset.py
    │   ├── training.py
    │   ├── agent.py
    │   └── deployment.py
    ├── services/           # 业务逻辑层
    │   ├── dataset.py
    │   ├── training.py
    │   ├── agent.py
    │   ├── deployment.py
    │   └── log.py
    ├── security/           # 安全与鉴权
    │   └── auth.py
    ├── integrations/       # 外部系统适配器
    │   ├── kubernetes/     # K8s 操作
    │   ├── mlflow/         # MLflow 客户端
    │   ├── lakefs/         # lakeFS 客户端
    │   └── object_store/   # S3/MinIO 客户端
    └── events/            # 事件系统
        └── handler.py
```

### 3.2 分层原则

| 层级 | 职责 | 约束 |
|------|------|------|
| **Endpoints** | 协议转换、请求验证、路由分发 | 只做 DTO 转换，不执行业务逻辑 |
| **Services** | 核心业务逻辑、事务编排 | 不直接访问数据库，通过 Repository |
| **Repositories** | 数据库 CRUD、数据一致性 | 单表/单实体操作，事务边界 |
| **Models** | 数据库实体定义 | 不包含业务逻辑 |
| **Integrations** | 外部系统交互 | 抽象为独立模块，可替换 |

---

## 4. 核心模块设计

### 4.1 多租户模块 (Tenant/Project)

**功能**：
- 租户创建、更新、删除
- 项目创建与管理
- 资源配额管理 (GPU Hours, Storage, Deployments)
- Kubernetes namespace 自动分配

**数据模型**：

```
Tenant (租户)
├── id: UUID (PK)
├── name: str (unique)
├── status: Enum (ACTIVE, SUSPENDED, DELETED)
├── quota_gpuHours: int
├── quota_storage_gb: int
├── quota_deployments: int
└── created_at, updated_at

Project (项目)
├── id: UUID (PK)
├── tenant_id: UUID (FK)
├── name: str
├── status: Enum (ACTIVE, SUSPENDED, DELETED)
├── namespace: str (K8s namespace, unique)
├── quota_gpuHours: int
├── quota_storage_gb: int
├── quota_deployments: int
└── created_at, updated_at
```

**关键约束**：
- 租户名全局唯一
- Project namespace 自动生成（tenant-project 格式）
- 配额支持租户级和项目级配置

### 4.2 数据集模块 (Dataset/DatasetVersion)

**功能**：
- 数据集创建与元数据管理
- 数据版本化（创建、分支、合并、回滚）
- 文件上传（直传 + 预签名 URL）
- 数据验证
- 数据集删除

**数据模型**：

```
Dataset
├── id: UUID (PK)
├── project_id: UUID (FK)
├── name: str
├── data_format: str (jsonl, parquet, csv, json)
├── storage_prefix: str (S3 路径)
├── schema_: Optional[str] (JSON Schema)
├── description: Optional[str]
└── created_at, updated_at

DatasetVersion
├── id: UUID (PK)
├── dataset_id: UUID (FK)
├── version: str (v1, v2, ...)
├── storage_prefix: str (版本存储路径)
├── file_size_bytes: Optional[int]
├── checksum: Optional[str] (MD5/SHA256)
├── status: Enum (CREATED, VALIDATING, VALIDATED, FAILED)
├── validation_errors: Optional[str] (JSON)
└── created_at, updated_at
```

**设计要点**：
- 对象存储路径：`projects/{project_id}/datasets/{name}/versions/{version}/{filename}`
- 支持预签名 URL 实现客户端直传
- lakeFS 集成用于高级版本控制（branch/merge）

### 4.3 训练与模型模块 (TrainingJob/Model/ModelVersion)

**功能**：
- 训练任务提交（基于数据集、模型、配置）
- 训练状态跟踪（queued, running, completed, failed）
- 模型注册与版本管理
- 模型 lineage 追踪
- MLflow 集成

**数据模型**：

```
TrainingJob
├── id: UUID (PK)
├── project_id: UUID (FK)
├── dataset_version_id: UUID (FK)
├── base_model_id: Optional[UUID] (FK)
├── name: str
├── config: JSON (训练参数)
├── status: Enum (QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED)
├── started_at: Optional[datetime]
├── completed_at: Optional[datetime]
├── error_message: Optional[str]
├── metrics: JSON
└── created_at, updated_at

Model
├── id: UUID (PK)
├── project_id: UUID (FK)
├── name: str
├── status: Enum (DRAFT, PUBLISHED, ARCHIVED)
├── latest_version_id: Optional[UUID] (FK)
└── created_at, updated_at

ModelVersion
├── id: UUID (PK)
├── model_id: UUID (FK)
├── version: str
├── training_job_id: Optional[UUID] (FK)
├── storage_prefix: str (模型文件路径)
├── mlflow_run_id: Optional[str]
├── metrics: JSON
├── status: Enum (DRAFT, PROMOTED, ARCHIVED)
└── created_at, updated_at
```

**训练流程**：
1. 提交 TrainingJob → 状态 QUEUED
2. K8s Job 调度执行 → 状态 RUNNING
3. 训练完成 → 创建 ModelVersion → 状态 COMPLETED
4. MLflow 记录实验指标和参数

### 4.4 Agent 模块 (AgentSpec/AgentRevision/AgentRun)

**功能**：
- Agent 规范定义（name, description, system_prompt, tools, model_binding）
- Agent 版本管理（revision）
- Agent 运行（触发执行）
- Agent 发布（部署到运行环境）

**数据模型**：

```
AgentSpec
├── id: UUID (PK)
├── project_id: UUID (FK)
├── name: str
├── description: Optional[str]
├── system_prompt: str
├── tools: JSON (工具定义)
├── model_binding: JSON (绑定的模型)
├── status: Enum (DRAFT, PUBLISHED, ARCHIVED)
└── created_at, updated_at

AgentRevision
├── id: UUID (PK)
├── agent_spec_id: UUID (FK)
├── revision: int (版本号)
├── spec_snapshot: JSON (完整快照)
├── status: Enum (DRAFT, PUBLISHED, ARCHIVED)
├── changelog: Optional[str]
└── created_at, updated_at

AgentRun
├── id: UUID (PK)
├── agent_revision_id: UUID (FK)
├── input_data: JSON
├── output_data: Optional[JSON]
├── status: Enum (PENDING, RUNNING, COMPLETED, FAILED, INTERRUPTED)
├── error_message: Optional[str]
├── started_at: Optional[datetime]
├── completed_at: Optional[datetime]
└── created_at, updated_at
```

**设计要点**：
- AgentSpec 存当前定义，AgentRevision 存历史快照
- 支持版本回滚
- AgentRun 记录每次执行的输入输出

### 4.5 部署模块 (Deployment)

**功能**：
- Agent 部署到推理服务
- 扩缩容管理
- 流量分配（灰度发布）
- 健康检查与回滚

**数据模型**：

```
Deployment
├── id: UUID (PK)
├── project_id: UUID (FK)
├── agent_revision_id: UUID (FK)
├── name: str
├── status: Enum (DEPLOYING, RUNNING, FAILED, STOPPED)
├── replicas: int
├── traffic_weight: int (0-100)
├── endpoint: str (推理端点 URL)
├── resources: JSON (CPU, Memory, GPU)
└── created_at, updated_at
```

**部署流程**：
1. 创建 Deployment → 状态 DEPLOYING
2. 调用 K8s/KServe API 创建 InferenceService
3. 等待服务 ready → 状态 RUNNING
4. 更新 endpoint 指向服务地址

### 4.6 事件与日志模块

**事件系统**：
- WebSocket 实时推送（/ws）
- SSE 长连接（/events/sse）
- 事件类型：job_status_changed, deployment_ready, agent_run_completed 等

**日志系统**：
- 训练日志（TrainingJob 日志）
- Agent 运行日志（AgentRun 日志）
- 部署日志（Deployment 事件）
- 日志存储：MinIO + Redis Stream

---

## 5. API 接口规范

### 5.1 API 路由结构

```
/api/v1
├── /tenants
│   ├── POST   /tenants              # 创建租户
│   ├── GET    /tenants              # 租户列表
│   ├── GET    /tenants/{id}         # 租户详情
│   ├── PATCH  /tenants/{id}         # 更新租户
│   └── DELETE /tenants/{id}         # 删除租户
├── /projects
│   ├── POST   /tenants/{id}/projects    # 创建项目
│   ├── GET    /tenants/{id}/projects    # 项目列表
│   ├── GET    /projects/{id}            # 项目详情
│   ├── PATCH  /projects/{id}            # 更新项目
│   └── DELETE /projects/{id}            # 删除项目
├── /datasets
│   ├── POST   /datasets                 # 创建数据集
│   ├── GET    /datasets                 # 数据集列表
│   ├── GET    /datasets/{id}            # 数据集详情
│   ├── PATCH  /datasets/{id}            # 更新数据集
│   ├── DELETE /datasets/{id}            # 删除数据集
│   ├── POST   /datasets/{id}/upload     # 上传文件
│   ├── GET    /datasets/{id}/versions   # 版本列表
│   ├── POST   /datasets/{id}/validate  # 验证版本
│   └── POST   /datasets/{id}/versions  # 创建版本
├── /training
│   ├── POST   /training/jobs                    # 提交训练任务
│   ├── GET    /training/jobs                    # 训练任务列表
│   ├── GET    /training/jobs/{id}               # 任务详情
│   ├── POST   /training/jobs/{id}/cancel        # 取消任务
│   ├── GET    /training/models                  # 模型列表
│   ├── GET    /training/models/{id}             # 模型详情
│   ├── GET    /training/models/{id}/versions    # 模型版本
│   └── POST   /training/models/{id}/promote      # 升级模型版本
├── /agents
│   ├── POST   /agents                   # 创建 Agent
│   ├── GET    /agents                   # Agent 列表
│   ├── GET    /agents/{id}              # Agent 详情
│   ├── PATCH  /agents/{id}               # 更新 Agent
│   ├── DELETE /agents/{id}              # 删除 Agent
│   ├── GET    /agents/{id}/revisions    # 版本列表
│   ├── POST   /agents/{id}/publish      # 发布新版本
│   ├── POST   /agents/{id}/runs         # 触发运行
│   └── GET    /agents/{id}/runs         # 运行记录
├── /deployments
│   ├── POST   /deployments                  # 创建部署
│   ├── GET    /deployments                  # 部署列表
│   ├── GET    /deployments/{id}             # 部署详情
│   ├── PATCH  /deployments/{id}             # 更新部署
│   ├── DELETE /deployments/{id}            # 删除部署
│   ├── POST   /deployments/{id}/scale      # 扩缩容
│   ├── POST   /deployments/{id}/rollback   # 回滚
│   └── GET    /deployments/{id}/health      # 健康检查
├── /logs
│   ├── GET    /logs/jobs/{job_id}           # 训练日志
│   ├── GET    /logs/runs/{run_id}          # Agent 运行日志
│   └── GET    /logs/deployments/{id}       # 部署日志
└── /events
    ├── GET    /events/sse                  # SSE 事件流
    └── POST   /events/publish              # 发布事件 (内部)
```

### 5.2 请求/响应规范

**通用响应格式**：
```json
// 成功
{
  "data": {...},
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 100
  }
}

// 错误
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [...]
  }
}
```

**分页参数**：
- `page`: 页码（默认 1）
- `page_size`: 每页数量（默认 20，最大 100）

**排序参数**：
- `sort_by`: 排序字段
- `order`: asc | desc

---

## 6. 安全与隔离

### 6.1 租户隔离

- **数据隔离**：Project 级别的 RBAC，查询强制带 project_id 过滤
- **资源隔离**：每个 Project 独立 K8s namespace
- **存储隔离**：对象存储路径带 project_id 前缀

### 6.2 认证与授权

- **认证**：JWT Token（Python-JOSE）
- **授权**：基于角色的访问控制（RBAC）
- **配额**：TokenPayload 携带 tenant_id 和 quota 信息

### 6.3 审计

- 记录所有 CRUD 操作到 AuditEvent 表
- 字段：tenant_id, project_id, user_id, operation, resource_type, resource_id, timestamp

---

## 7. 可观测性

### 7.1 日志

- 结构化日志（JSON 格式）
- 级别：DEBUG, INFO, WARNING, ERROR
- 上下文：tenant_id, project_id, request_id

### 7.2 指标

- API 响应时间
- 训练任务成功率
- 部署成功率
- 资源使用率（GPU, Memory, Storage）

### 7.3 追踪

- OpenTelemetry 集成
- Trace ID 贯穿整个请求链路

---

## 8. 第一阶段实现范围

优先实现最小闭环：

1. **多租户与配额**：Tenant/Project CRUD，配额管理
2. **数据集管理**：Dataset/Version CRUD，预签名上传
3. **训练任务**：TrainingJob 提交与状态跟踪
4. **模型注册**：Model/ModelVersion 管理
5. **Agent 管理**：AgentSpec/Revision 管理
6. **部署**：Deployment 创建与状态
7. **事件流**：WebSocket/SSE 实时推送
8. **日志**：训练和运行日志查询

---

## 9. 附录

### 9.1 依赖版本

- Python: 3.11+
- FastAPI: 0.115.0+
- SQLAlchemy: 2.0.36+
- PostgreSQL: 16
- Redis: 7
- Kubernetes: 1.28+

### 9.2 配置项

所有配置通过环境变量或 `.env` 文件管理，详见 `backend/.env.example`