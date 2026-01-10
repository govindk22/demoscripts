pip install requests pandas python-dateutil

import requests
import pandas as pd
from datetime import datetime, timedelta
from dateutil.parser import isoparse

class GitLabCICDAdoption:
    def __init__(self, base_url, token, is_saas=False):
        """
        base_url:
          SaaS  -> https://gitlab.com
          Self  -> https://gitlab.company.com
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        self.rest_api = f"{self.base_url}/api/v4"
        self.graphql_api = f"{self.base_url}/api/graphql"

    # -------------------------------
    # REST API
    # -------------------------------
    def get_group_projects_rest(self, group_id):
        projects = []
        page = 1

        while True:
            resp = requests.get(
                f"{self.rest_api}/groups/{group_id}/projects",
                headers=self.headers,
                params={
                    "include_subgroups": True,
                    "per_page": 100,
                    "page": page
                }
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            projects.extend(data)
            page += 1

        return projects

    def get_project_pipelines_rest(self, project_id, since_days=30):
        since = (datetime.utcnow() - timedelta(days=since_days)).isoformat()
        resp = requests.get(
            f"{self.rest_api}/projects/{project_id}/pipelines",
            headers=self.headers,
            params={"updated_after": since, "per_page": 100}
        )
        resp.raise_for_status()
        return resp.json()

    # -------------------------------
    # GraphQL API (Faster at Scale)
    # -------------------------------
    def get_group_projects_graphql(self, group_full_path):
        query = """
        query ($fullPath: ID!) {
          group(fullPath: $fullPath) {
            projects(first: 100, includeSubgroups: true) {
              nodes {
                id
                name
                fullPath
                lastPipeline {
                  createdAt
                }
              }
            }
          }
        }
        """
        resp = requests.post(
            self.graphql_api,
            headers=self.headers,
            json={"query": query, "variables": {"fullPath": group_full_path}}
        )
        resp.raise_for_status()
        return resp.json()["data"]["group"]["projects"]["nodes"]

    # -------------------------------
    # Adoption Computation
    # -------------------------------
    def compute_adoption_rest(self, group_id):
        projects = self.get_group_projects_rest(group_id)
        cutoff = datetime.utcnow() - timedelta(days=30)

        rows = []

        for p in projects:
            pipelines = self.get_project_pipelines_rest(p["id"])
            last_pipeline_at = pipelines[0]["updated_at"] if pipelines else None

            active_30d = False
            if last_pipeline_at:
                active_30d = isoparse(last_pipeline_at) >= cutoff

            rows.append({
                "project_id": p["id"],
                "project_name": p["name"],
                "project_path": p["path_with_namespace"],
                "ci_enabled": bool(pipelines),
                "active_ci_30d": active_30d,
                "pipelines_last_30d": len(pipelines),
                "last_pipeline_at": last_pipeline_at
            })

        df = pd.DataFrame(rows)
        return self._summarize(df)

    def compute_adoption_graphql(self, group_full_path):
        projects = self.get_group_projects_graphql(group_full_path)
        cutoff = datetime.utcnow() - timedelta(days=30)

        rows = []
        for p in projects:
            last_pipeline_at = (
                p["lastPipeline"]["createdAt"]
                if p["lastPipeline"]
                else None
            )

            active_30d = False
            if last_pipeline_at:
                active_30d = isoparse(last_pipeline_at) >= cutoff

            rows.append({
                "project_name": p["name"],
                "project_path": p["fullPath"],
                "ci_enabled": bool(last_pipeline_at),
                "active_ci_30d": active_30d,
                "last_pipeline_at": last_pipeline_at
            })

        df = pd.DataFrame(rows)
        return self._summarize(df)

    # -------------------------------
    # Summary Metrics
    # -------------------------------
    def _summarize(self, df):
        total = len(df)
        with_ci = df["ci_enabled"].sum()
        active_30d = df["active_ci_30d"].sum()

        summary = {
            "total_projects": total,
            "projects_with_ci": int(with_ci),
            "active_ci_projects_30d": int(active_30d),
            "adoption_rate_pct": round((with_ci / total) * 100, 2) if total else 0
        }

        return df, summary

    # -------------------------------
    # Export
    # -------------------------------
    @staticmethod
    def export_csv(df, filename):
        df.to_csv(filename, index=False)

#GitLab SaaS (GraphQL – Recommended)
client = GitLabCICDAdoption(
    base_url="https://gitlab.com",
    token="GL_TOKEN"
)

df, summary = client.compute_adoption_graphql("mygroup/myorg")

print(summary)
df.head()

✅ Self-Managed (REST)
client = GitLabCICDAdoption(
    base_url="https://gitlab.company.com",
    token="GL_TOKEN"
)

df, summary = client.compute_adoption_rest(group_id=1234)

client.export_csv(df, "cicd_adoption.csv")

############

import requests
import pandas as pd
from datetime import datetime, timedelta
from dateutil.parser import isoparse
from collections import defaultdict

JOB_PATTERNS = {
    "sast": ["sast", "semgrep", "bandit", "snyk"],
    "dast": ["dast", "zap"],
    "test": ["test", "pytest", "junit", "mocha"],
    "build": ["build", "compile", "npm", "maven", "gradle"],
    "deploy": ["deploy", "helm", "kubectl", "terraform"]
}

class GitLabCICDAdoption:
    def __init__(self, base_url, token):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self.rest_api = f"{self.base_url}/api/v4"
        self.graphql_api = f"{self.base_url}/api/graphql"

    # -------------------------------
    # REST helpers
    # -------------------------------
    def _get(self, url, params=None):
        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_group_projects(self, group_id):
        projects, page = [], 1
        while True:
            data = self._get(
                f"{self.rest_api}/groups/{group_id}/projects",
                params={"include_subgroups": True, "per_page": 100, "page": page}
            )
            if not data:
                break
            projects.extend(data)
            page += 1
        return projects

    def get_pipelines(self, project_id, since_days=30):
        since = (datetime.utcnow() - timedelta(days=since_days)).isoformat()
        return self._get(
            f"{self.rest_api}/projects/{project_id}/pipelines",
            params={"updated_after": since, "per_page": 50}
        )

    def get_jobs(self, project_id, pipeline_id):
        return self._get(
            f"{self.rest_api}/projects/{project_id}/pipelines/{pipeline_id}/jobs",
            params={"per_page": 100}
        )

    # -------------------------------
    # Job Pattern Classification
    # -------------------------------
    def classify_job(self, job_name):
        lname = job_name.lower()
        for category, keywords in JOB_PATTERNS.items():
            if any(k in lname for k in keywords):
                return category
        return "other"

    # -------------------------------
    # Adoption & Job Analysis
    # -------------------------------
    def compute_adoption_with_jobs(self, group_id):
        projects = self.get_group_projects(group_id)
        cutoff = datetime.utcnow() - timedelta(days=30)
        rows = []

        for p in projects:
            pipelines = self.get_pipelines(p["id"])
            job_stats = defaultdict(int)
            total_jobs = 0

            for pipe in pipelines:
                jobs = self.get_jobs(p["id"], pipe["id"])
                total_jobs += len(jobs)

                for j in jobs:
                    category = self.classify_job(j["name"])
                    job_stats[category] += 1

            last_pipeline_at = pipelines[0]["updated_at"] if pipelines else None
            active_30d = (
                isoparse(last_pipeline_at) >= cutoff
                if last_pipeline_at else False
            )

            rows.append({
                "project_id": p["id"],
                "project_name": p["name"],
                "project_path": p["path_with_namespace"],
                "pipelines_last_30d": len(pipelines),
                "avg_jobs_per_pipeline": round(
                    total_jobs / len(pipelines), 2
                ) if pipelines else 0,
                "sast_jobs": job_stats["sast"],
                "dast_jobs": job_stats["dast"],
                "test_jobs": job_stats["test"],
                "build_jobs": job_stats["build"],
                "deploy_jobs": job_stats["deploy"],
                "other_jobs": job_stats["other"],
                "ci_enabled": bool(pipelines),
                "active_ci_30d": active_30d,
                "last_pipeline_at": last_pipeline_at
            })

        df = pd.DataFrame(rows)
        return df, self._summary(df)

    # -------------------------------
    # Summary
    # -------------------------------
    def _summary(self, df):
        return {
            "total_projects": len(df),
            "projects_with_ci": int(df["ci_enabled"].sum()),
            "active_ci_projects_30d": int(df["active_ci_30d"].sum()),
            "avg_jobs_per_pipeline_org": round(
                df["avg_jobs_per_pipeline"].mean(), 2
            )
        }

    # -------------------------------
    # Export
    # -------------------------------
    @staticmethod
    def export_csv(df, filename):
        df.to_csv(filename, index=False)


########## 
gitlab_cicd_adoption.py
import requests
import pandas as pd
from datetime import datetime, timedelta
from dateutil.parser import isoparse
from collections import defaultdict

# -------------------------------
# Classification Patterns
# -------------------------------

STAGE_PATTERNS = {
    "build": ["build", "compile", "package"],
    "test": ["test", "verify", "qa"],
    "security": ["security", "sast", "dast", "scan"],
    "deploy": ["deploy", "release", "delivery"]
}

JOB_PATTERNS = {
    "build": ["build", "compile", "npm", "maven", "gradle"],
    "test": ["test", "pytest", "junit", "mocha"],
    "security": ["sast", "dast", "semgrep", "bandit", "snyk", "zap"],
    "deploy": ["deploy", "helm", "kubectl", "terraform"]
}

CATEGORIES = ["build", "test", "security", "deploy", "other"]

# -------------------------------
# Main Client
# -------------------------------

class GitLabCICDAdoption:
    def __init__(self, base_url: str, token: str):
        """
        base_url:
          SaaS  -> https://gitlab.com
          Self  -> https://gitlab.company.com
        """
        self.base_url = base_url.rstrip("/")
        self.rest_api = f"{self.base_url}/api/v4"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    # -------------------------------
    # REST Helpers
    # -------------------------------

    def _get(self, url, params=None):
        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_group_projects(self, group_id: int):
        projects = []
        page = 1
        while True:
            data = self._get(
                f"{self.rest_api}/groups/{group_id}/projects",
                params={
                    "include_subgroups": True,
                    "per_page": 100,
                    "page": page
                }
            )
            if not data:
                break
            projects.extend(data)
            page += 1
        return projects

    def get_pipelines(self, project_id: int, since_days=30):
        since = (datetime.utcnow() - timedelta(days=since_days)).isoformat()
        return self._get(
            f"{self.rest_api}/projects/{project_id}/pipelines",
            params={"updated_after": since, "per_page": 50}
        )

    def get_jobs(self, project_id: int, pipeline_id: int):
        return self._get(
            f"{self.rest_api}/projects/{project_id}/pipelines/{pipeline_id}/jobs",
            params={"per_page": 100}
        )

    # -------------------------------
    # Classification Logic (Hybrid)
    # -------------------------------

    @staticmethod
    def _match_pattern(value: str, patterns: dict):
        value = value.lower()
        for category, keywords in patterns.items():
            if any(k in value for k in keywords):
                return category
        return None

    def classify_job(self, job: dict):
        """
        Hybrid classification:
        1) Stage-based match (highest priority)
        2) Job-name match
        3) Fallback to 'other'
        """
        stage = job.get("stage", "") or ""
        name = job.get("name", "") or ""

        stage_match = self._match_pattern(stage, STAGE_PATTERNS)
        if stage_match:
            return stage_match

        job_match = self._match_pattern(name, JOB_PATTERNS)
        if job_match:
            return job_match

        return "other"

    # -------------------------------
    # Pipeline Profile
    # -------------------------------

    @staticmethod
    def derive_pipeline_profile(stage_presence: set):
        if {"build", "test", "security", "deploy"}.issubset(stage_presence):
            return "Advanced CI/CD"
        if {"build", "test", "deploy"}.issubset(stage_presence):
            return "Standard CI/CD"
        if {"build", "test"}.issubset(stage_presence):
            return "CI Only"
        if {"deploy"}.issubset(stage_presence):
            return "CD Only"
        return "Basic / Ad-hoc"

    # -------------------------------
    # Main Computation
    # -------------------------------

    def compute_group_adoption(self, group_id: int, since_days=30):
        projects = self.get_group_projects(group_id)
        cutoff = datetime.utcnow() - timedelta(days=since_days)

        rows = []

        for project in projects:
            pipelines = self.get_pipelines(project["id"], since_days)

            job_totals = defaultdict(int)
            stage_presence = set()
            total_jobs = 0

            for pipeline in pipelines:
                jobs = self.get_jobs(project["id"], pipeline["id"])
                total_jobs += len(jobs)

                for job in jobs:
                    category = self.classify_job(job)
                    job_totals[category] += 1
                    stage_presence.add(category)

            last_pipeline_at = pipelines[0]["updated_at"] if pipelines else None
            active_30d = (
                isoparse(last_pipeline_at) >= cutoff
                if last_pipeline_at else False
            )

            profile = self.derive_pipeline_profile(stage_presence)

            row = {
                "project_id": project["id"],
                "project_name": project["name"],
                "project_path": project["path_with_namespace"],
                "pipelines_last_30d": len(pipelines),
                "avg_jobs_per_pipeline": round(
                    total_jobs / len(pipelines), 2
                ) if pipelines else 0,

                # Job counts (hybrid)
                "build_jobs": job_totals["build"],
                "test_jobs": job_totals["test"],
                "security_jobs": job_totals["security"],
                "deploy_jobs": job_totals["deploy"],
                "other_jobs": job_totals["other"],

                # Stage presence flags
                "has_build": "build" in stage_presence,
                "has_test": "test" in stage_presence,
                "has_security": "security" in stage_presence,
                "has_deploy": "deploy" in stage_presence,

                "pipeline_profile": profile,
                "ci_enabled": bool(pipelines),
                "active_ci_30d": active_30d,
                "last_pipeline_at": last_pipeline_at
            }

            rows.append(row)

        df = pd.DataFrame(rows)
        return df, self._summary(df)

    # -------------------------------
    # Summary Metrics
    # -------------------------------

    @staticmethod
    def _summary(df: pd.DataFrame):
        total = len(df)
        with_ci = int(df["ci_enabled"].sum())
        active = int(df["active_ci_30d"].sum())

        return {
            "total_projects": total,
            "projects_with_ci": with_ci,
            "active_ci_projects_30d": active,
            "ci_adoption_pct": round((with_ci / total) * 100, 2) if total else 0,
            "avg_jobs_per_pipeline_org": round(
                df["avg_jobs_per_pipeline"].mean(), 2
            ) if not df.empty else 0
        }

    # -------------------------------
    # Export Helpers
    # -------------------------------

    @staticmethod
    def export_csv(df: pd.DataFrame, filename: str):
        df.to_csv(filename, index=False)
