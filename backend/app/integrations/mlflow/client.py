"""MLflow client for model registry and experiment tracking"""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

import mlflow
from mlflow.tracking import MlflowClient

from app.core.config import settings


class MLflowService:
    """MLflow service for experiment tracking and model registry"""

    def __init__(self):
        # Set tracking URI
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        self.client = MlflowClient()

    # === Experiment Operations ===

    def create_experiment(self, name: str, description: str = "") -> str:
        """Create MLflow experiment"""
        exp = mlflow.create_experiment(name, description=description)
        return exp

    def get_experiment(self, name: str) -> Optional[Dict[str, Any]]:
        """Get experiment by name"""
        exp = mlflow.get_experiment_by_name(name)
        if exp:
            return {
                "id": exp.experiment_id,
                "name": exp.name,
                "artifact_location": exp.artifact_location,
                "lifecycle_stage": exp.lifecycle_stage,
            }
        return None

    def list_experiments(self, filter_str: str = "") -> List[Dict[str, Any]]:
        """List experiments"""
        exps = mlflow.list_experiments(filter_string=filter_str)
        return [
            {
                "id": e.experiment_id,
                "name": e.name,
                "artifact_location": e.artifact_location,
                "lifecycle_stage": e.lifecycle_stage,
            }
            for e in exps
        ]

    def delete_experiment(self, name: str) -> None:
        """Delete experiment"""
        exp = mlflow.get_experiment_by_name(name)
        if exp:
            mlflow.delete_experiment(exp.experiment_id)

    # === Run Operations ===

    def start_run(
        self,
        experiment_name: str,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """Start a new run"""
        exp = mlflow.get_experiment_by_name(experiment_name)
        if not exp:
            exp_id = mlflow.create_experiment(experiment_name)
        else:
            exp_id = exp.experiment_id

        run = mlflow.start_run(
            experiment_id=exp_id,
            run_name=run_name,
            tags=tags or {},
        )
        return run.info.run_id

    def log_metric(self, run_id: str, key: str, value: float, step: Optional[int] = None) -> None:
        """Log metric"""
        mlflow.log_metric(key, value, step=step)

    def log_metrics(self, run_id: str, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        """Log multiple metrics"""
        for key, value in metrics.items():
            mlflow.log_metric(key, value, step=step)

    def log_param(self, run_id: str, key: str, value: str) -> None:
        """Log parameter"""
        mlflow.log_param(key, value)

    def log_params(self, run_id: str, params: Dict[str, str]) -> None:
        """Log multiple parameters"""
        mlflow.log_params(params)

    def log_artifact(self, run_id: str, local_path: str, artifact_path: Optional[str] = None) -> None:
        """Log artifact"""
        mlflow.log_artifact(local_path, artifact_path)

    def log_model(self, run_id: str, flavor: str, artifact_path: str, **kwargs) -> None:
        """Log model"""
        # This is a simplified version - actual implementation depends on the model flavor
        mlflow.log_dict(kwargs, f"{artifact_path}/model_metadata.json")

    def end_run(self, run_id: str, status: str = "FINISHED") -> None:
        """End run"""
        mlflow.end_run(status=status)

    def get_run(self, run_id: str) -> Dict[str, Any]:
        """Get run info"""
        run = mlflow.get_run(run_id)
        return {
            "id": run.info.run_id,
            "experiment_id": run.info.experiment_id,
            "status": run.info.status,
            "start_time": datetime.fromtimestamp(run.info.start_time / 1000).isoformat(),
            "end_time": datetime.fromtimestamp(run.info.end_time / 1000).isoformat() if run.info.end_time else None,
            "metrics": {k: v.value for k, v in run.data.metrics.items()},
            "params": run.data.params,
            "tags": run.data.tags,
        }

    def list_runs(
        self,
        experiment_name: str,
        max_results: int = 100,
        filter_str: str = "",
    ) -> List[Dict[str, Any]]:
        """List runs in experiment"""
        exp = mlflow.get_experiment_by_name(experiment_name)
        if not exp:
            return []

        runs = mlflow.search_runs(
            experiment_ids=[exp.experiment_id],
            filter_string=filter_str,
            max_results=max_results,
        )

        return [
            {
                "id": r.info.run_id,
                "status": r.info.status,
                "start_time": datetime.fromtimestamp(r.info.start_time / 1000).isoformat(),
                "metrics": {k: v.value for k, v in r.data.metrics.items()},
                "params": r.data.params,
            }
            for r in runs.itertuples()
        ]

    def delete_run(self, run_id: str) -> None:
        """Delete run"""
        mlflow.delete_run(run_id)

    # === Model Registry Operations ===

    def register_model(
        self,
        name: str,
        run_id: str,
        artifact_path: str,
        description: str = "",
    ) -> Dict[str, Any]:
        """Register model from run"""
        model_uri = f"runs://{run_id}/{artifact_path}"
        model = mlflow.register_model(model_uri, name)
        # Update description if provided
        if description:
            self.client.update_model_version(name, model.version, description=description)
        return {
            "name": model.name,
            "version": model.version,
            "uri": model_uri,
        }

    def get_model(self, name: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get model version"""
        if version:
            try:
                mv = self.client.get_model_version(name, version)
                return {
                    "name": mv.name,
                    "version": mv.version,
                    "stage": mv.current_stage,
                    "status": mv.status,
                    "description": mv.description,
                    "created_at": mv.creation_timestamp,
                    "updated_at": mv.last_updated_timestamp,
                }
            except mlflow.exceptions.MlflowException:
                return None
        else:
            # Get latest version
            try:
                mv = self.client.get_latest_versions(name, stages=["None"])[0]
                return {
                    "name": mv.name,
                    "version": mv.version,
                    "stage": mv.current_stage,
                    "status": mv.status,
                }
            except (mlflow.exceptions.MlflowException, IndexError):
                return None

    def list_models(self, name: str) -> List[Dict[str, Any]]:
        """List all versions of a model"""
        try:
            versions = self.client.get_model_version_stages(name)
            return [
                {
                    "name": name,
                    "version": v,
                    "stage": self.client.get_model_version(name, v).current_stage,
                }
                for v in versions
            ]
        except mlflow.exceptions.MlflowException:
            return []

    def transition_stage(
        self,
        name: str,
        version: int,
        stage: str,
        archive_existing: bool = True,
    ) -> None:
        """Transition model version to new stage"""
        self.client.transition_model_version_stage(
            name, version, stage, archive_existing_versions=archive_existing
        )

    def update_model_description(self, name: str, version: int, description: str) -> None:
        """Update model version description"""
        self.client.update_model_version(name, version, description=description)

    def delete_model_version(self, name: str, version: int) -> None:
        """Delete model version"""
        self.client.delete_model_version(name, version)

    def delete_model(self, name: str) -> None:
        """Delete all versions of a model"""
        self.client.delete_registered_model(name)

    def get_model_uri(self, name: str, version: Optional[int] = None, stage: Optional[str] = None) -> str:
        """Get model URI for loading"""
        if version:
            return f"models:/{name}/{version}"
        elif stage:
            return f"models:/{name}/{stage}"
        else:
            return f"models:/{name}/latest"

    # === Model Serving ===

    def create_model_version(
        self,
        name: str,
        source: str,
        run_id: Optional[str] = None,
        description: str = "",
    ) -> Dict[str, Any]:
        """Create model version from source"""
        mv = self.client.create_model_version(name, source, run_id, description)
        return {
            "name": mv.name,
            "version": mv.version,
            "source": mv.source,
            "run_id": mv.run_id,
        }


# Singleton instance
_mlflow_service: Optional[MLflowService] = None


def get_mlflow_service() -> MLflowService:
    """Get or create MLflow service"""
    global _mlflow_service
    if _mlflow_service is None:
        _mlflow_service = MLflowService()
    return _mlflow_service


mlflow_service = get_mlflow_service()
