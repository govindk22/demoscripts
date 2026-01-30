import requests
import pandas as pd
from datetime import datetime, timedelta
from dateutil.parser import isoparse

class GitLabCICDAdoption:
    def __init__(self, base_url, token, is_saas=False):
     
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