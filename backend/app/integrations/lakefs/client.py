"""lakeFS client for data version management"""
import base64
from typing import Optional, List, Dict, Any
import httpx

from app.core.config import settings


class LakeFSClient:
    """lakeFS client for data versioning"""

    def __init__(self):
        self.endpoint = settings.lakefs_endpoint
        self.access_key = settings.lakefs_access_key
        self.secret_key = settings.lakefs_secret_key
        self._client = httpx.Client(
            base_url=self.endpoint,
            auth=(self.access_key, self.secret_key),
        )

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make request to lakeFS"""
        response = self._client.request(method, f"/api/v1{path}", **kwargs)
        response.raise_for_status()
        return response.json()

    # === Repository Operations ===

    def create_repository(
        self,
        name: str,
        storage_namespace: str,
        description: str = "",
        default_branch: str = "main",
    ) -> Dict[str, Any]:
        """Create a lakeFS repository"""
        return self._request(
            "POST",
            "/repositories",
            json={
                "name": name,
                "storage_namespace": storage_namespace,
                "description": description,
                "default_branch": default_branch,
            },
        )

    def get_repository(self, repo: str) -> Dict[str, Any]:
        """Get repository info"""
        return self._request("GET", f"/repositories/{repo}")

    def list_repositories(self, prefix: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """List repositories"""
        result = self._request(
            "GET",
            "/repositories",
            params={"prefix": prefix, "amount": limit},
        )
        return result.get("results", [])

    def delete_repository(self, repo: str) -> None:
        """Delete repository"""
        self._request("DELETE", f"/repositories/{repo}")

    # === Branch Operations ===

    def create_branch(
        self,
        repo: str,
        name: str,
        source_branch: str = "main",
    ) -> Dict[str, Any]:
        """Create a new branch"""
        return self._request(
            "POST",
            f"/repositories/{repo}/branches",
            json={
                "name": name,
                "source": source_branch,
            },
        )

    def get_branch(self, repo: str, branch: str) -> Dict[str, Any]:
        """Get branch info"""
        return self._request("GET", f"/repositories/{repo}/branches/{branch}")

    def list_branches(self, repo: str, limit: int = 100) -> List[Dict[str, Any]]:
        """List branches"""
        result = self._request(
            "GET",
            f"/repositories/{repo}/branches",
            params={"amount": limit},
        )
        return result.get("results", [])

    def delete_branch(self, repo: str, branch: str) -> None:
        """Delete branch"""
        self._request("DELETE", f"/repositories/{repo}/branches/{branch}")

    # === File Operations ===

    def upload_file(
        self,
        repo: str,
        branch: str,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        """Upload file to lakeFS"""
        import json

        content_b64 = base64.b64encode(content).decode("utf-8")
        return self._request(
            "POST",
            f"/repositories/{repo}/branches/{branch}/objects",
            json={
                "path": path,
                "content_type": content_type,
                "data": content_b64,
            },
        )

    def get_file(self, repo: str, ref: str, path: str) -> bytes:
        """Get file content"""
        response = self._client.get(
            f"/api/v1/repositories/{repo}/refs/{ref}/objects/{path}",
        )
        response.raise_for_status()
        data = response.json()
        return base64.b64decode(data["data"])

    def delete_file(self, repo: str, branch: str, path: str) -> Dict[str, Any]:
        """Delete file"""
        return self._request(
            "DELETE",
            f"/repositories/{repo}/branches/{branch}/objects",
            json={"path": path},
        )

    def list_files(
        self,
        repo: str,
        ref: str,
        path: str = "",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List files in path"""
        result = self._request(
            "GET",
            f"/repositories/{repo}/refs/{ref}/objects/ls",
            params={"path": path, "amount": limit},
        )
        return result.get("results", [])

    # === Commit Operations ===

    def commit(
        self,
        repo: str,
        branch: str,
        message: str,
        author: str = "agent-studio",
    ) -> Dict[str, Any]:
        """Commit changes"""
        return self._request(
            "POST",
            f"/repositories/{repo}/commits",
            json={
                "message": message,
                "author": author,
            },
            params={"branch": branch},
        )

    def get_commit(self, repo: str, commit_id: str) -> Dict[str, Any]:
        """Get commit info"""
        return self._request("GET", f"/repositories/{repo}/commits/{commit_id}")

    def log_commits(
        self,
        repo: str,
        branch: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get commit log"""
        result = self._request(
            "GET",
            f"/repositories/{repo}/commits",
            params={"ref": branch, "amount": limit},
        )
        return result.get("results", [])

    # === Tag Operations ===

    def create_tag(
        self,
        repo: str,
        name: str,
        commit_id: str,
    ) -> Dict[str, Any]:
        """Create tag"""
        return self._request(
            "POST",
            f"/repositories/{repo}/tags",
            json={
                "id": name,
                "commit_id": commit_id,
            },
        )

    def get_tag(self, repo: str, tag: str) -> Dict[str, Any]:
        """Get tag info"""
        return self._request("GET", f"/repositories/{repo}/tags/{tag}")

    def list_tags(self, repo: str, limit: int = 100) -> List[Dict[str, Any]]:
        """List tags"""
        result = self._request(
            "GET",
            f"/repositories/{repo}/tags",
            params={"amount": limit},
        )
        return result.get("results", [])

    def delete_tag(self, repo: str, tag: str) -> None:
        """Delete tag"""
        self._request("DELETE", f"/repositories/{repo}/tags/{tag}")

    # === Merge Operations ===

    def merge(
        self,
        repo: str,
        source_ref: str,
        destination_branch: str,
        message: str = "",
    ) -> Dict[str, Any]:
        """Merge branches"""
        return self._request(
            "POST",
            f"/repositories/{repo}/merges",
            json={
                "from_ref": source_ref,
                "message": message or f"Merge {source_ref} into {destination_branch}",
            },
            params={"destination_branch": destination_branch},
        )

    def get_mergeability(
        self,
        repo: str,
        source_ref: str,
        destination_branch: str,
    ) -> Dict[str, Any]:
        """Check if merge is possible"""
        return self._request(
            "GET",
            f"/repositories/{repo}/merges/{source_ref}/{destination_branch}",
        )

    def close(self):
        """Close client"""
        self._client.close()


# Singleton instance
_lakefs_client: Optional[LakeFSClient] = None


def get_lakefs_client() -> LakeFSClient:
    """Get or create lakeFS client"""
    global _lakefs_client
    if _lakefs_client is None:
        _lakefs_client = LakeFSClient()
    return _lakefs_client


lakefs_client = get_lakefs_client()
