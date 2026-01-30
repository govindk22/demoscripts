import csv
import os
import fnmatch
import requests
import pandas as pd
from datetime import datetime, timedelta
from dateutil.parser import isoparse
from collections import defaultdict
from typing import List, Dict, Optional, Tuple

# -------------------------------
# Classification Patterns
# -------------------------------

STAGE_PATTERNS = {
    "build": ["build", "compile", "package"],
    "test": ["test", "verify", "qa"],
    "scan": ["scan", "sast", "dast", "security scan"],
    "sonar": ["sonar", "sonarqube", "sonar-scanner"],
    "veracode": ["veracode", "veracode scan"],
    "deploy": ["deploy", "release", "delivery"]
}

JOB_PATTERNS = {
    "build": ["build", "compile", "npm", "maven", "gradle", "dotnet", "docker build"],
    "test": ["test", "pytest", "junit", "mocha", "jest", "unit-test", "integration-test"],
    "scan": ["prisma""image-can", "sast", "dast", "security", "semgrep", "bandit", "snyk", "zap", "trivy"],
    "sonar": ["sonar", "sonarqube", "sonar-scanner", "sonar-analysis"],
    "veracode": ["veracode", "veracode scan", "veracode-analysis"],
    "deploy": ["deploy", "helm", "kubectl", "terraform", "ansible", "release"]
}

# Required stages for weighted completeness
REQUIRED_STAGES = ["build", "test", "scan", "sonar", "veracode", "deploy"]
STAGE_WEIGHT = 100 / len(REQUIRED_STAGES)  # Each stage is worth ~16.67%

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

    def get_group_by_path(self, group_path: str) -> Optional[Dict]:
        """
        Get group information by path.
        
        Args:
            group_path: Group path (e.g., 'mycompany/team1')
            
        Returns:
            Group dictionary or None if not found
        """
        try:
            encoded_path = requests.utils.quote(group_path, safe='')
            return self._get(f"{self.rest_api}/groups/{encoded_path}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"Group '{group_path}' not found")
            else:
                print(f"Error fetching group '{group_path}': {e}")
            return None
        except Exception as e:
            print(f"Unexpected error fetching group '{group_path}': {e}")
            return None

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
    # CSV Loading
    # -------------------------------

    def load_groups_from_csv(self, groups_file: str = 'gitlab-groups.csv') -> List[Tuple[str, str, List[str]]]:
        """
        Load groups from CSV file.
        
        Args:
            groups_file: Path to groups CSV file
            
        Returns:
            List of tuples: (application_name, group_path, exclude_patterns)
        """
        groups = []
        if not os.path.exists(groups_file):
            print(f"Groups file {groups_file} does not exist.")
            return groups
        
        with open(groups_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                application = row.get('application', '').strip()
                group_path = row.get('gitlab-group', '').strip()
                excludes = row.get('excludes', '').strip()
                
                if group_path:
                    exclude_patterns = [p.strip() for p in excludes.split(',') if p.strip()] if excludes else []
                    groups.append((application, group_path, exclude_patterns))
        
        return groups

    # -------------------------------
    # Classification Logic
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

    @staticmethod
    def calculate_weighted_completeness(stage_presence: set) -> float:
        """
        Calculate weighted completeness based on required stages.
        Each stage (build, test, scan, sonar, veracode, deploy) = 100/6 = ~16.67%
        
        Args:
            stage_presence: Set of present stages
            
        Returns:
            Completeness percentage (0-100)
        """
        present_count = sum(1 for stage in REQUIRED_STAGES if stage in stage_presence)
        return round(present_count * STAGE_WEIGHT, 2)

    # -------------------------------
    # Main Computation
    # -------------------------------

    def compute_group_adoption(self, group_id: int, group_name: str = None, 
                              group_path: str = None, exclude_patterns: List[str] = None,
                              since_days=30):
        """
        Compute CI/CD adoption for a group by ID.
        
        Args:
            group_id: GitLab group ID
            group_name: Optional group name for output
            group_path: Optional group path for output
            exclude_patterns: List of project path patterns to exclude
            since_days: Number of days to look back
            
        Returns:
            Tuple of (DataFrame, summary_dict, excluded_count)
        """
        all_projects = self.get_group_projects(group_id)
        cutoff = datetime.utcnow() - timedelta(days=since_days)

        rows = []
        excluded_count = 0

        for project in all_projects:
            project_path = project.get("path_with_namespace", "")
            
            # Check if project should be excluded
            if exclude_patterns:
                if any(fnmatch.fnmatch(project_path, p) or 
                      fnmatch.fnmatch(project_path.split('/')[-1], p) 
                      for p in exclude_patterns):
                    excluded_count += 1
                    continue

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

            weighted_completeness = self.calculate_weighted_completeness(stage_presence)

            row = {
                "group_name": group_name or "",
                "group_path": group_path or "",
                "project_id": project["id"],
                "project_name": project["name"],
                "project_path": project_path,
                "pipelines_last_30d": len(pipelines),
                "avg_jobs_per_pipeline": round(
                    total_jobs / len(pipelines), 2
                ) if pipelines else 0,

                # Job counts by type
                "build_jobs": job_totals["build"],
                "test_jobs": job_totals["test"],
                "scan_jobs": job_totals["scan"],
                "sonar_jobs": job_totals["sonar"],
                "veracode_jobs": job_totals["veracode"],
                "deploy_jobs": job_totals["deploy"],
                "other_jobs": job_totals["other"],

                # Stage presence flags
                "has_build": "build" in stage_presence,
                "has_test": "test" in stage_presence,
                "has_scan": "scan" in stage_presence,
                "has_sonar": "sonar" in stage_presence,
                "has_veracode": "veracode" in stage_presence,
                "has_deploy": "deploy" in stage_presence,

                "weighted_completeness_pct": weighted_completeness,
                "ci_enabled": bool(pipelines),
                "active_ci_30d": active_ci_30d,
                "last_pipeline_at": last_pipeline_at
            }

            rows.append(row)

        df = pd.DataFrame(rows)
        return df, self._summary(df, group_name or group_path, excluded_count), excluded_count

    def compute_group_adoption_by_path(self, group_path: str, application_name: str = None,
                                      exclude_patterns: List[str] = None,
                                      since_days=30):
        """
        Compute CI/CD adoption for a group by path.
        
        Args:
            group_path: Group path (e.g., 'mycompany/team1')
            application_name: Optional application/group name
            exclude_patterns: List of project path patterns to exclude
            since_days: Number of days to look back
            
        Returns:
            Tuple of (DataFrame, summary_dict, excluded_count) or (None, None, 0) if group not found
        """
        group_info = self.get_group_by_path(group_path)
        if not group_info:
            return None, None, 0
        
        group_id = group_info["id"]
        group_name = application_name or group_info.get("name", group_path)
        
        return self.compute_group_adoption(group_id, group_name, group_path, exclude_patterns, since_days)

    def compute_all_groups_adoption(self, groups_file: str = 'gitlab-groups.csv',
                                   since_days=30) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Compute CI/CD adoption for all groups from CSV file.
        
        Args:
            groups_file: Path to groups CSV file
            since_days: Number of days to look back
            
        Returns:
            Tuple of (detailed_dataframe, summary_dataframe)
        """
        groups = self.load_groups_from_csv(groups_file)
        
        all_detailed_rows = []
        summary_rows = []
        
        for application_name, group_path, exclude_patterns in groups:
            print(f"\nProcessing group: {application_name} ({group_path})")
            
            df, summary, excluded_count = self.compute_group_adoption_by_path(
                group_path, 
                application_name,
                exclude_patterns,
                since_days
            )
            
            if df is not None and not df.empty:
                all_detailed_rows.append(df)
                
                # Add excluded count to summary
                summary['excluded_from_metrics'] = excluded_count
                summary_rows.append(summary)
                
                print(f"  Found {len(df)} projects, {excluded_count} excluded, CI adoption: {summary['ci_adoption_pct']}%")
        
        # Combine all detailed data
        if all_detailed_rows:
            detailed_df = pd.concat(all_detailed_rows, ignore_index=True)
        else:
            detailed_df = pd.DataFrame()
        
        # Create summary DataFrame
        if summary_rows:
            summary_df = pd.DataFrame(summary_rows)
        else:
            summary_df = pd.DataFrame()
        
        return detailed_df, summary_df

    def generate_executive_summary(self, groups_file: str = 'gitlab-groups.csv',
                                  since_days=30) -> Dict:
        """
        Generate executive summary statistics across all groups.
        
        Args:
            groups_file: Path to groups CSV file
            since_days: Number of days to look back
            
        Returns:
            Dictionary with executive summary metrics
        """
        detailed_df, summary_df = self.compute_all_groups_adoption(groups_file, since_days)
        
        if detailed_df.empty:
            return {
                "total_groups": 0,
                "total_projects": 0,
                "total_excluded": 0,
                "total_projects_with_ci": 0,
                "overall_ci_adoption_pct": 0,
                "overall_active_ci_pct": 0,
                "overall_weighted_completeness_pct": 0,
                "avg_jobs_per_pipeline": 0,
                "job_counts_across_ci_projects": {},
                "groups_summary": []
            }
        
        # Filter to projects with CI for job counting
        ci_projects_df = detailed_df[detailed_df["ci_enabled"] == True]
        
        # Overall statistics
        total_projects = len(detailed_df)
        total_excluded = summary_df["excluded_from_metrics"].sum() if "excluded_from_metrics" in summary_df.columns else 0
        total_with_ci = int(detailed_df["ci_enabled"].sum())
        total_active_ci = int(detailed_df["active_ci_30d"].sum())
        overall_adoption = round((total_with_ci / total_projects) * 100, 2) if total_projects > 0 else 0
        overall_active_ci_pct = round((total_active_ci / total_projects) * 100, 2) if total_projects > 0 else 0
        avg_jobs = round(detailed_df["avg_jobs_per_pipeline"].mean(), 2) if not detailed_df.empty else 0
        
        # Weighted completeness (average across projects with CI)
        overall_completeness = round(
            ci_projects_df["weighted_completeness_pct"].mean(), 2
        ) if not ci_projects_df.empty else 0
        
        # Job counts across projects with CI
        job_counts = {
            "build": int(ci_projects_df["build_jobs"].sum()) if not ci_projects_df.empty else 0,
            "test": int(ci_projects_df["test_jobs"].sum()) if not ci_projects_df.empty else 0,
            "scan": int(ci_projects_df["scan_jobs"].sum()) if not ci_projects_df.empty else 0,
            "sonar": int(ci_projects_df["sonar_jobs"].sum()) if not ci_projects_df.empty else 0,
            "veracode": int(ci_projects_df["veracode_jobs"].sum()) if not ci_projects_df.empty else 0,
            "deploy": int(ci_projects_df["deploy_jobs"].sum()) if not ci_projects_df.empty else 0,
            "other": int(ci_projects_df["other_jobs"].sum()) if not ci_projects_df.empty else 0
        }
        
        # Per-group summary
        groups_summary = []
        if not summary_df.empty:
            for _, row in summary_df.iterrows():
                # Get job counts for this group's CI projects
                group_name = row.get("group_name", "")
                group_ci_projects = detailed_df[
                    (detailed_df["group_name"] == group_name) & 
                    (detailed_df["ci_enabled"] == True)
                ]
                group_all_projects = detailed_df[detailed_df["group_name"] == group_name]
                
                group_job_counts = {
                    "build": int(group_ci_projects["build_jobs"].sum()) if not group_ci_projects.empty else 0,
                    "test": int(group_ci_projects["test_jobs"].sum()) if not group_ci_projects.empty else 0,
                    "scan": int(group_ci_projects["scan_jobs"].sum()) if not group_ci_projects.empty else 0,
                    "sonar": int(group_ci_projects["sonar_jobs"].sum()) if not group_ci_projects.empty else 0,
                    "veracode": int(group_ci_projects["veracode_jobs"].sum()) if not group_ci_projects.empty else 0,
                    "deploy": int(group_ci_projects["deploy_jobs"].sum()) if not group_ci_projects.empty else 0
                }
                
                # Weighted completeness for this group
                group_completeness = round(
                    group_ci_projects["weighted_completeness_pct"].mean(), 2
                ) if not group_ci_projects.empty else 0
                
                # Active CI % for this group
                group_active_ci = int(group_all_projects["active_ci_30d"].sum()) if not group_all_projects.empty else 0
                group_total = len(group_all_projects)
                group_active_ci_pct = round((group_active_ci / group_total) * 100, 2) if group_total > 0 else 0
                
                groups_summary.append({
                    "application_name": row.get("application_name", ""),
                    "group_name": group_name,
                    "group_path": row.get("group_path", ""),
                    "total_projects": int(row.get("total_projects", 0)),
                    "excluded_from_metrics": int(row.get("excluded_from_metrics", 0)),
                    "projects_with_ci": int(row.get("projects_with_ci", 0)),
                    "ci_adoption_pct": round(row.get("ci_adoption_pct", 0), 2),
                    "active_ci_pct": group_active_ci_pct,
                    "avg_jobs_per_pipeline": round(row.get("avg_jobs_per_pipeline_org", 0), 2),
                    "weighted_completeness_pct": group_completeness,
                    "job_counts": group_job_counts
                })
        
        return {
            "total_groups": len(summary_df),
            "total_projects": total_projects,
            "total_excluded": int(total_excluded),
            "total_projects_with_ci": total_with_ci,
            "overall_ci_adoption_pct": overall_adoption,
            "overall_active_ci_pct": overall_active_ci_pct,
            "overall_weighted_completeness_pct": overall_completeness,
            "avg_jobs_per_pipeline": avg_jobs,
            "job_counts_across_ci_projects": job_counts,
            "groups_summary": groups_summary,
            "period_days": since_days
        }

    # -------------------------------
    # Summary Metrics
    # -------------------------------

    @staticmethod
    def _summary(df: pd.DataFrame, group_name: str = None, excluded_count: int = 0):
        total = len(df)
        with_ci = int(df["ci_enabled"].sum())
        active = int(df["active_ci_30d"].sum())
        
        # Calculate weighted completeness for projects with CI
        ci_projects = df[df["ci_enabled"] == True]
        avg_completeness = round(
            ci_projects["weighted_completeness_pct"].mean(), 2
        ) if not ci_projects.empty else 0

        return {
            "group_name": group_name or "",
            "total_projects": total,
            "projects_with_ci": with_ci,
            "active_ci_projects_30d": active,
            "active_ci_pct": round((active / total) * 100, 2) if total else 0,
            "ci_adoption_pct": round((with_ci / total) * 100, 2) if total else 0,
            "avg_jobs_per_pipeline_org": round(
                df["avg_jobs_per_pipeline"].mean(), 2
            ) if not df.empty else 0,
            "weighted_completeness_pct": avg_completeness
        }

    # -------------------------------
    # Export Helpers
    # -------------------------------

    @staticmethod
    def export_csv(df: pd.DataFrame, filename: str):
        df.to_csv(filename, index=False)

    def export_executive_summary(self, groups_file: str = 'gitlab-groups.csv',
                                since_days=30,
                                detailed_output: str = 'cicd-adoption-detailed.csv',
                                summary_output: str = 'cicd-adoption-summary.csv',
                                executive_output: str = 'cicd-adoption-executive-summary.txt'):
        """
        Generate and export all CI/CD adoption reports.
        
        Args:
            groups_file: Path to groups CSV file
            since_days: Number of days to look back
            detailed_output: Output file for detailed project-level data
            summary_output: Output file for group-level summary
            executive_output: Output file for executive summary text report
        """
        # Generate data
        detailed_df, summary_df = self.compute_all_groups_adoption(groups_file, since_days)
        exec_summary = self.generate_executive_summary(groups_file, since_days)
        
        # Export detailed data
        if not detailed_df.empty:
            self.export_csv(detailed_df, detailed_output)
            print(f"\nDetailed data exported to: {detailed_output}")
        
        # Export summary data
        if not summary_df.empty:
            self.export_csv(summary_df, summary_output)
            print(f"Summary data exported to: {summary_output}")
        
        # Export executive summary
        with open(executive_output, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("CI/CD ADOPTION EXECUTIVE SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Analysis Period: Last {exec_summary['period_days']} days\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("OVERALL STATISTICS\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Groups Analyzed: {exec_summary['total_groups']}\n")
            f.write(f"Total Projects: {exec_summary['total_projects']}\n")
            f.write(f"Excluded from Metrics: {exec_summary['total_excluded']}\n")
            f.write(f"Projects with CI/CD: {exec_summary['total_projects_with_ci']}\n")
            f.write(f"Overall CI/CD Adoption: {exec_summary['overall_ci_adoption_pct']}%\n")
            f.write(f"Overall Active CI % (Last 30 days): {exec_summary['overall_active_ci_pct']}%\n")
            f.write(f"Overall Weighted Completeness: {exec_summary['overall_weighted_completeness_pct']}%\n")
            f.write(f"Average Jobs per Pipeline: {exec_summary['avg_jobs_per_pipeline']}\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("JOB COUNTS ACROSS PROJECTS WITH CI/CD\n")
            f.write("-" * 80 + "\n")
            for job_type, count in exec_summary['job_counts_across_ci_projects'].items():
                f.write(f"{job_type.capitalize()}: {count} jobs\n")
            f.write("\n")
            
            f.write("-" * 80 + "\n")
            f.write("PER-GROUP SUMMARY\n")
            f.write("-" * 80 + "\n")
            for group in exec_summary['groups_summary']:
                f.write(f"\n{group['application_name']} ({group['group_path']}):\n")
                f.write(f"  Total Projects: {group['total_projects']}\n")
                f.write(f"  Excluded from Metrics: {group['excluded_from_metrics']}\n")
                f.write(f"  Projects with CI/CD: {group['projects_with_ci']}\n")
                f.write(f"  CI/CD Adoption: {group['ci_adoption_pct']}%\n")
                f.write(f"  Active CI % (Last 30 days): {group['active_ci_pct']}%\n")
                f.write(f"  Weighted Completeness: {group['weighted_completeness_pct']}%\n")
                f.write(f"  Avg Jobs per Pipeline: {group['avg_jobs_per_pipeline']}\n")
                f.write(f"  Job Counts (across CI projects):\n")
                for job_type, count in group['job_counts'].items():
                    f.write(f"    {job_type.capitalize()}: {count} jobs\n")
        
        print(f"Executive summary exported to: {executive_output}")


# Example usage
if __name__ == '__main__':
    import os
    
    # Configuration
    GITLAB_URL = os.getenv('GITLAB_URL', 'https://gitlab.com')
    GITLAB_TOKEN = os.getenv('GITLAB_TOKEN', '')
    GROUPS_FILE = 'gitlab-groups.csv'
    
    if GITLAB_TOKEN:
        client = GitLabCICDAdoption(GITLAB_URL, GITLAB_TOKEN)
        
        # Generate and export all reports
        client.export_executive_summary(
            groups_file=GROUPS_FILE,
            since_days=30
        )
    else:
        print("Please set GITLAB_TOKEN environment variable")