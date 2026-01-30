import os
import json
import requests
import pandas as pd

from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
from collections import defaultdict
from typing import Dict, List, Tuple


# ============================================================
# Job + Stage Classification Patterns
# ============================================================

JOB_PATTERNS = {
    "sast": ["sast", "semgrep", "bandit", "snyk"],
    "dast": ["dast", "zap"],
    "test": ["test", "pytest", "junit", "mocha"],
    "build": ["build", "compile", "npm", "maven", "gradle"],
    "deploy": ["deploy", "helm", "kubectl", "terraform"],
}

STAGE_PATTERNS = {
    "security": ["sast", "dast", "security"],
    "testing": ["test", "qa"],
    "build": ["build", "compile"],
    "deploy": ["deploy", "release", "prod"],
}


# ============================================================
# GitLab CI/CD Adoption + Maturity Analyzer
# ============================================================

class GitLabCICDMaturity:
    """
    Enterprise GitLab CI/CD Adoption + Compliance + Maturity Analyzer

    Adds:
      ✅ JSON export for dashboards
      ✅ Pipeline success/failure tracking
      ✅ Missing compliance detection (SAST/Test/Deploy)
      ✅ Team rollups and maturity scoring
    """

    def __init__(self, base_url: str, token: str):

        self.base_url = base_url.rstrip("/")

        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        self.rest_api = f"{self.base_url}/api/v4"
        self.graphql_api = f"{self.base_url}/api/graphql"

    # ============================================================
    # REST Helper
    # ============================================================

    def _get(self, url: str, params=None):
        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json()

    # ============================================================
    # GraphQL Pagination: Fetch ALL Projects
    # ============================================================

    def get_all_projects_graphql(self, group_full_path: str):

        query = """
        query ($fullPath: ID!, $cursor: String) {
          group(fullPath: $fullPath) {
            projects(first: 100, after: $cursor, includeSubgroups: true) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                id
                name
                fullPath
                namespace {
                  fullPath
                }
              }
            }
          }
        }
        """

        all_projects = []
        cursor = None

        while True:
            resp = requests.post(
                self.graphql_api,
                headers=self.headers,
                json={
                    "query": query,
                    "variables": {"fullPath": group_full_path, "cursor": cursor},
                },
            )
            resp.raise_for_status()

            data = resp.json()["data"]["group"]["projects"]

            all_projects.extend(data["nodes"])

            if not data["pageInfo"]["hasNextPage"]:
                break

            cursor = data["pageInfo"]["endCursor"]

        return all_projects

    # ============================================================
    # REST Pipelines + Jobs
    # ============================================================

    def get_pipelines(self, project_id: int, since_days=30):

        since = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()

        return self._get(
            f"{self.rest_api}/projects/{project_id}/pipelines",
            params={"updated_after": since, "per_page": 20},
        )

    def get_pipeline_jobs(self, project_id: int, pipeline_id: int):

        return self._get(
            f"{self.rest_api}/projects/{project_id}/pipelines/{pipeline_id}/jobs",
            params={"per_page": 100},
        )

    # ============================================================
    # Job + Stage Classification
    # ============================================================

    def classify_job(self, job_name: str):

        lname = job_name.lower()
        for cat, keywords in JOB_PATTERNS.items():
            if any(k in lname for k in keywords):
                return cat
        return "other"

    def classify_stage(self, stage_name: str):

        lname = stage_name.lower()
        for cat, keywords in STAGE_PATTERNS.items():
            if any(k in lname for k in keywords):
                return cat
        return "other"

    # ============================================================
    # CI Maturity Score
    # ============================================================

    def maturity_score(self, row: Dict) -> int:

        score = 0

        if row["ci_enabled"]:
            score += 25

        if row["pipelines_last_days"] > 5:
            score += 10

        if row["test_jobs"] > 0:
            score += 15

        if row["sast_jobs"] > 0:
            score += 20

        if row["deploy_jobs"] > 0:
            score += 15

        if row["success_rate"] >= 80:
            score += 15

        return min(score, 100)

    # ============================================================
    # Missing Compliance Flags
    # ============================================================

    def compliance_flags(self, row: Dict):

        flags = []

        if row["sast_jobs"] == 0:
            flags.append("NO_SAST")

        if row["deploy_jobs"] == 0:
            flags.append("NO_DEPLOY")

        if row["test_jobs"] == 0:
            flags.append("NO_TESTS")

        if row["success_rate"] < 50:
            flags.append("UNSTABLE_PIPELINES")

        return flags

    # ============================================================
    # ✅ Main Project Analytics
    # ============================================================

    def compute_project_adoption(self, group_full_path: str, since_days=30):

        projects = self.get_all_projects_graphql(group_full_path)

        rows = []

        for p in projects:

            project_id = int(p["id"].split("/")[-1])
            namespace = p["namespace"]["fullPath"]

            pipelines = self.get_pipelines(project_id, since_days)

            job_stats = defaultdict(int)
            stage_stats = defaultdict(int)

            total_jobs = 0
            total_success = 0
            total_failed = 0

            stage_names = set()

            # -----------------------------
            # Process Pipelines
            # -----------------------------
            for pipe in pipelines[:5]:

                if pipe["status"] == "success":
                    total_success += 1
                elif pipe["status"] == "failed":
                    total_failed += 1

                jobs = self.get_pipeline_jobs(project_id, pipe["id"])
                total_jobs += len(jobs)

                for j in jobs:

                    job_cat = self.classify_job(j["name"])
                    job_stats[job_cat] += 1

                    if j.get("stage"):
                        stage_cat = self.classify_stage(j["stage"])
                        stage_stats[stage_cat] += 1
                        stage_names.add(j["stage"])

            # Pipeline success rate %
            total_runs = total_success + total_failed
            success_rate = round((total_success / total_runs) * 100, 2) if total_runs else 0

            row = {
                "team_namespace": namespace,
                "project_name": p["name"],
                "project_path": p["fullPath"],

                "ci_enabled": bool(pipelines),
                "pipelines_last_days": len(pipelines),

                "success_pipelines": total_success,
                "failed_pipelines": total_failed,
                "success_rate": success_rate,

                "avg_jobs_per_pipeline": round(
                    total_jobs / len(pipelines), 2
                ) if pipelines else 0,

                "sast_jobs": job_stats["sast"],
                "test_jobs": job_stats["test"],
                "build_jobs": job_stats["build"],
                "deploy_jobs": job_stats["deploy"],

                "stages_used": len(stage_names),
            }

            row["ci_maturity_score"] = self.maturity_score(row)
            row["compliance_flags"] = self.compliance_flags(row)

            rows.append(row)

        df = pd.DataFrame(rows)

        return df, self.group_rollup(df)

    # ============================================================
    # Team/Subgroup Rollup
    # ============================================================

    def group_rollup(self, df):

        org_summary = {
            "total_projects": len(df),
            "projects_with_ci": int(df["ci_enabled"].sum()),
            "avg_success_rate": round(df["success_rate"].mean(), 2),
            "avg_maturity_score_org": round(df["ci_maturity_score"].mean(), 2),
        }

        team_rollup = (
            df.groupby("team_namespace")
            .agg(
                projects=("project_name", "count"),
                ci_enabled=("ci_enabled", "sum"),
                avg_score=("ci_maturity_score", "mean"),
                avg_success=("success_rate", "mean"),
                sast=("sast_jobs", "sum"),
                deploy=("deploy_jobs", "sum"),
            )
            .reset_index()
        )

        return org_summary, team_rollup

    # ============================================================
    # ✅ Export CSV + Dashboard JSON
    # ============================================================

    @staticmethod
    def export_reports(df_projects, df_teams, org_summary):

        # CSV exports
        df_projects.to_csv("cicd_projects_report.csv", index=False)
        df_teams.to_csv("cicd_team_rollup.csv", index=False)

        # Dashboard JSON export
        dashboard = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "org_summary": org_summary,
            "teams": df_teams.to_dict(orient="records"),
            "projects": df_projects.to_dict(orient="records"),
        }

        with open("cicd_dashboard.json", "w", encoding="utf-8") as f:
            json.dump(dashboard, f, indent=2)

        print("\n✅ Exported Reports:")
        print("   cicd_projects_report.csv")
        print("   cicd_team_rollup.csv")
        print("   cicd_dashboard.json")


# ============================================================
# Runner
# ============================================================

if __name__ == "__main__":

    GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")
    TOKEN = os.getenv("GITLAB_TOKEN")

    if not TOKEN:
        print("❌ Please set GITLAB_TOKEN")
        exit(1)

    GROUP_FULL_PATH = "gk-poc-team01"

    client = GitLabCICDMaturity(GITLAB_URL, TOKEN)

    df_projects, (summary, df_teams) = client.compute_project_adoption(
        GROUP_FULL_PATH,
        since_days=30
    )

    print("\n--- Org Summary ---")
    print(summary)

    client.export_reports(df_projects, df_teams, summary)
