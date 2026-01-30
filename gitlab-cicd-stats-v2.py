import requests
import pandas as pd
from datetime import datetime, timedelta
from dateutil.parser import isoparse
  
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
 

if __name__ == '__main__':
    # Configuration
    GITLAB_URL = os.getenv('GITLAB_URL', 'https://gitlab.com')
    GITLAB_TOKEN = os.getenv('GITLAB_TOKEN', '')
    CSV_FILE = 'gitlab-members.csv'
    
    if GITLAB_TOKEN:
     
        client = GitLabCICDAdoption(
            base_url= GITLAB_URL,
            token= GITLAB_TOKEN
        )

        df, summary = client.compute_adoption_graphql("gk-poc-team01")

        print(summary)
        df.head()
 

        df, summary = client.compute_adoption_rest(group_id=1234)

        client.export_csv(df, "cicd_adoption.csv")
 
        
    else:
        print("Please set GITLAB_TOKEN environment variable")