#!/bin/bash
# Setup script for Agent Studio - WSL version

set -e

echo "=== Agent Studio Local Setup (WSL) ==="

# Check if running in WSL
if grep -qi microsoft /proc/version; then
    echo "Running on WSL"
    # Check if Docker Desktop is installed and running
    if ! docker info >/dev/null 2>&1; then
        echo "Please start Docker Desktop and ensure it's accessible from WSL"
        exit 1
    fi
fi

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed."; exit 1; }
command -v kind >/dev/null 2>&1 || { echo "Kind is required but not installed."; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required but not installed."; exit 1; }

# Start docker containers
echo "Starting Docker containers..."
docker compose up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 10

# Create kind cluster
echo "Creating kind cluster..."
if kind get clusters 2>/dev/null | grep -q agent-studio; then
    echo "Cluster already exists, deleting..."
    kind delete cluster --name agent-studio
fi
kind create cluster --config kind-config.yaml --wait 5m

# Install ingress controller
echo "Installing ingress controller..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml

# Install metallb for LoadBalancer
echo "Installing MetalLB..."
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.5/config/manifests/metallb-native.yaml

# Wait for ingress to be ready
echo "Waiting for ingress to be ready..."
kubectl wait --namespace ingress-nginx \
    --for=condition=ready pod \
    --selector=app.kubernetes.io/component=controller \
    --timeout=120s || true

# Create namespaces for tenants
echo "Creating namespaces..."
kubectl create namespace agent-studio-system || true
kubectl create namespace agent-studio-jobs || true

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Services:"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo "  - MinIO: http://localhost:9000 (console: http://localhost:9001)"
echo "  - Kind cluster: agent-studio"
echo ""
echo "Next steps:"
echo "  1. Install Python dependencies: cd backend && pip install -e ."
echo "  2. Run database migrations: cd backend && alembic upgrade head"
echo "  3. Start FastAPI: cd backend && uvicorn app.main:app --reload"
