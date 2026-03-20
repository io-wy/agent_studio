#!/bin/bash
# Test script for Agent Studio API - WSL version
# Must be run AFTER setup.sh and backend is running

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
API_BASE="${BASE_URL}/api/v1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Generate random string for unique names
RANDOM_ID=$(date +%s%N | sha256sum | head -c 8)

# Test token (simplified - in production use proper JWT)
TEST_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJ0ZW5hbnRfaWQiOiJ0ZXN0LXRlbmFudCIsInJvbGUiOiJhZG1pbiJ9.test"

echo "========================================"
echo "Agent Studio API Test Suite"
echo "========================================"
echo "Base URL: $BASE_URL"
echo ""

# Check if backend is running
info "Checking if backend is running..."
if curl -s -f "${BASE_URL}/health" > /dev/null; then
    pass "Backend is running"
else
    fail "Backend is NOT running at ${BASE_URL}"
    echo "Please start backend first: cd backend && uvicorn app.main:app --reload"
    exit 1
fi

# ========================================
# Test 1: Tenant CRUD
# ========================================
echo ""
echo "=== Test 1: Tenant CRUD ==="

# Create tenant
TENANT_RESPONSE=$(curl -s -X POST "${API_BASE}/tenants" \
    -H "Authorization: Bearer ${TEST_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"test-tenant-${RANDOM_ID}\",
        \"quota_gpuHours\": 1000,
        \"quota_storage_gb\": 100,
        \"quota_deployments\": 5
    }")

TENANT_ID=$(echo $TENANT_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$TENANT_ID" ]; then
    pass "Create tenant: ${TENANT_ID}"
else
    fail "Create tenant failed: $TENANT_RESPONSE"
fi

# Get tenant
TENANT_GET=$(curl -s -X GET "${API_BASE}/tenants/${TENANT_ID}" \
    -H "Authorization: Bearer ${TEST_TOKEN}")

if echo "$TENANT_GET" | grep -q "\"name\":\"test-tenant"; then
    pass "Get tenant"
else
    fail "Get tenant failed"
fi

# List tenants
TENANTS=$(curl -s -X GET "${API_BASE}/tenants" \
    -H "Authorization: Bearer ${TEST_TOKEN}")

if echo "$TENANTS" | grep -q "test-tenant"; then
    pass "List tenants"
else
    fail "List tenants failed"
fi

# ========================================
# Test 2: Project CRUD
# ========================================
echo ""
echo "=== Test 2: Project CRUD ==="

# Create project
PROJECT_RESPONSE=$(curl -s -X POST "${API_BASE}/projects" \
    -H "Authorization: Bearer ${TEST_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"tenant_id\": \"${TENANT_ID}\",
        \"name\": \"test-project-${RANDOM_ID}\",
        \"description\": \"Test project\",
        \"quota_gpuHours\": 100,
        \"quota_storage_gb\": 10,
        \"quota_deployments\": 2
    }")

PROJECT_ID=$(echo $PROJECT_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$PROJECT_ID" ]; then
    pass "Create project: ${PROJECT_ID}"
else
    fail "Create project failed: $PROJECT_RESPONSE"
fi

# Get project
PROJECT_GET=$(curl -s -X GET "${API_BASE}/projects/${PROJECT_ID}" \
    -H "Authorization: Bearer ${TEST_TOKEN}")

if echo "$PROJECT_GET" | grep -q "test-project"; then
    pass "Get project"
else
    fail "Get project failed"
fi

# List projects
PROJECTS=$(curl -s -X GET "${API_BASE}/projects?tenant_id=${TENANT_ID}" \
    -H "Authorization: Bearer ${TEST_TOKEN}")

if echo "$PROJECTS" | grep -q "test-project"; then
    pass "List projects"
else
    fail "List projects failed"
fi

# Update project quota
QUOTA_RESPONSE=$(curl -s -X POST "${API_BASE}/projects/${PROJECT_ID}/quotas" \
    -H "Authorization: Bearer ${TEST_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"quota_gpuHours": 200}')

if echo "$QUOTA_RESPONSE" | grep -q "200"; then
    pass "Update project quota"
else
    fail "Update project quota failed"
fi

# ========================================
# Test 3: Dataset CRUD
# ========================================
echo ""
echo "=== Test 3: Dataset CRUD ==="

# Create dataset
DATASET_RESPONSE=$(curl -s -X POST "${API_BASE}/datasets" \
    -H "Authorization: Bearer ${TEST_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"project_id\": \"${PROJECT_ID}\",
        \"name\": \"test-dataset-${RANDOM_ID}\",
        \"description\": \"Test dataset\",
        \"data_format\": \"jsonl\"
    }")

DATASET_ID=$(echo $DATASET_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$DATASET_ID" ]; then
    pass "Create dataset: ${DATASET_ID}"
else
    fail "Create dataset failed: $DATASET_RESPONSE"
fi

# Get dataset
DATASET_GET=$(curl -s -X GET "${API_BASE}/datasets/${DATASET_ID}" \
    -H "Authorization: Bearer ${TEST_TOKEN}")

if echo "$DATASET_GET" | grep -q "test-dataset"; then
    pass "Get dataset"
else
    fail "Get dataset failed"
fi

# List datasets
DATASETS=$(curl -s -X GET "${API_BASE}/datasets?project_id=${PROJECT_ID}" \
    -H "Authorization: Bearer ${TEST_TOKEN}")

if echo "$DATASETS" | grep -q "test-dataset"; then
    pass "List datasets"
else
    fail "List datasets failed"
fi

# ========================================
# Test 4: Training Job CRUD
# ========================================
echo ""
echo "=== Test 4: Training Job CRUD ==="

# Create training job
TRAINING_RESPONSE=$(curl -s -X POST "${API_BASE}/training-jobs" \
    -H "Authorization: Bearer ${TEST_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"project_id\": \"${PROJECT_ID}\",
        \"name\": \"test-training-${RANDOM_ID}\",
        \"description\": \"Test training\",
        \"base_model\": \"meta-llama/Llama-3-8b\",
        \"training_type\": \"lora\"
    }")

TRAINING_ID=$(echo $TRAINING_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$TRAINING_ID" ]; then
    pass "Create training job: ${TRAINING_ID}"
else
    fail "Create training job failed: $TRAINING_RESPONSE"
fi

# Get training job
TRAINING_GET=$(curl -s -X GET "${API_BASE}/training-jobs/${TRAINING_ID}" \
    -H "Authorization: Bearer ${TEST_TOKEN}")

if echo "$TRAINING_GET" | grep -q "test-training"; then
    pass "Get training job"
else
    fail "Get training job failed"
fi

# List training jobs
TRAININGS=$(curl -s -X GET "${API_BASE}/training-jobs?project_id=${PROJECT_ID}" \
    -H "Authorization: Bearer ${TEST_TOKEN}")

if echo "$TRAININGS" | grep -q "test-training"; then
    pass "List training jobs"
else
    fail "List training jobs failed"
fi

# ========================================
# Test 5: Model CRUD
# ========================================
echo ""
echo "=== Test 5: Model CRUD ==="

# Create model
MODEL_RESPONSE=$(curl -s -X POST "${API_BASE}/models" \
    -H "Authorization: Bearer ${TEST_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"project_id\": \"${PROJECT_ID}\",
        \"name\": \"test-model-${RANDOM_ID}\",
        \"description\": \"Test model\",
        \"base_model\": \"meta-llama/Llama-3-8b\"
    }")

MODEL_ID=$(echo $MODEL_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$MODEL_ID" ]; then
    pass "Create model: ${MODEL_ID}"
else
    fail "Create model failed: $MODEL_RESPONSE"
fi

# Get model
MODEL_GET=$(curl -s -X GET "${API_BASE}/models/${MODEL_ID}" \
    -H "Authorization: Bearer ${TEST_TOKEN}")

if echo "$MODEL_GET" | grep -q "test-model"; then
    pass "Get model"
else
    fail "Get model failed"
fi

# List models
MODELS=$(curl -s -X GET "${API_BASE}/models?project_id=${PROJECT_ID}" \
    -H "Authorization: Bearer ${TEST_TOKEN}")

if echo "$MODELS" | grep -q "test-model"; then
    pass "List models"
else
    fail "List models failed"
fi

# ========================================
# Test 6: Agent CRUD
# ========================================
echo ""
echo "=== Test 6: Agent CRUD ==="

# Create agent
AGENT_RESPONSE=$(curl -s -X POST "${API_BASE}/agents" \
    -H "Authorization: Bearer ${TEST_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"project_id\": \"${PROJECT_ID}\",
        \"name\": \"test-agent-${RANDOM_ID}\",
        \"description\": \"Test agent\",
        \"system_prompt\": \"You are a helpful assistant.\",
        \"tools\": \"[]\",
        \"model_binding\": \"gpt-4\"
    }")

AGENT_ID=$(echo $AGENT_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$AGENT_ID" ]; then
    pass "Create agent: ${AGENT_ID}"
else
    fail "Create agent failed: $AGENT_RESPONSE"
fi

# Get agent
AGENT_GET=$(curl -s -X GET "${API_BASE}/agents/${AGENT_ID}" \
    -H "Authorization: Bearer ${TEST_TOKEN}")

if echo "$AGENT_GET" | grep -q "test-agent"; then
    pass "Get agent"
else
    fail "Get agent failed"
fi

# List agents
AGENTS=$(curl -s -X GET "${API_BASE}/agents?project_id=${PROJECT_ID}" \
    -H "Authorization: Bearer ${TEST_TOKEN}")

if echo "$AGENTS" | grep -q "test-agent"; then
    pass "List agents"
else
    fail "List agents failed"
fi

# ========================================
# Test 7: Agent Revision
# ========================================
echo ""
echo "=== Test 7: Agent Revision ==="

# Create agent revision
REVISION_RESPONSE=$(curl -s -X POST "${API_BASE}/agents/${AGENT_ID}/revisions" \
    -H "Authorization: Bearer ${TEST_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"agent_spec_id\": \"${AGENT_ID}\",
        \"system_prompt\": \"You are a helpful assistant v2.\",
        \"tools\": \"[]\",
        \"model_binding\": \"gpt-4\"
    }")

REVISION_ID=$(echo $REVISION_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$REVISION_ID" ]; then
    pass "Create agent revision: ${REVISION_ID}"
else
    fail "Create agent revision failed: $REVISION_RESPONSE"
fi

# List revisions
REVISIONS=$(curl -s -X GET "${API_BASE}/agents/${AGENT_ID}/revisions" \
    -H "Authorization: Bearer ${TEST_TOKEN}")

if echo "$REVISIONS" | grep -q "revision"; then
    pass "List agent revisions"
else
    fail "List agent revisions failed"
fi

# ========================================
# Test 8: Deployment CRUD
# ========================================
echo ""
echo "=== Test 8: Deployment CRUD ==="

# Create deployment (without model version - should fail)
DEPLOYMENT_RESPONSE=$(curl -s -X POST "${API_BASE}/deployments" \
    -H "Authorization: Bearer ${TEST_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"project_id\": \"${PROJECT_ID}\",
        \"name\": \"test-deployment-${RANDOM_ID}\",
        \"deployment_type\": \"kserve\",
        \"replicas\": 1
    }")

# This should fail because no model_version_id or agent_revision_id
if echo "$DEPLOYMENT_RESPONSE" | grep -q "error\|detail"; then
    pass "Deployment validation works (correctly rejected without model/agent)"
else
    fail "Deployment should require model_version_id or agent_revision_id"
fi

# ========================================
# Test 9: Health Check
# ========================================
echo ""
echo "=== Test 9: Health Check ==="

HEALTH=$(curl -s "${BASE_URL}/health")
if echo "$HEALTH" | grep -q "healthy"; then
    pass "Health check"
else
    fail "Health check failed"
fi

# ========================================
# Summary
# ========================================
echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo -e "${GREEN}Passed: ${PASSED}${NC}"
echo -e "${RED}Failed: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
