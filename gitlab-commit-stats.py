import csv
import os
import fnmatch
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import gitlab

from gitlab_projects import GitLabProjectManager


# ============================================================
#  Data Model
# ============================================================

@dataclass
class CommitStats:
    """User commit statistics."""

    user_id: int
    user_full_name: str
    username: str
    email: str

    commits_count: int = 0
    merge_commits_count: int = 0

    has_rapid_commits: bool = False
    rapid_commits_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "user_full_name": self.user_full_name,
            "username": self.username,
            "email": self.email,
            "commits_count": self.commits_count,
            "merge_commits_count": self.merge_commits_count,
            "has_rapid_commits": self.has_rapid_commits,
            "rapid_commits_count": self.rapid_commits_count,
        }


# ============================================================
#  Main Commit Stats Collector
# ============================================================

class GitLabCommitStats:
    """Collects GitLab commit stats across projects + branches."""

    def __init__(self, gitlab_url: str, private_token: str):
        self.gitlab_url = gitlab_url
        self.private_token = private_token

        self.gl = gitlab.Gitlab(gitlab_url, private_token=private_token)
        self.gl.auth()

        self.projects = GitLabProjectManager(gitlab_url, private_token)

    # ============================================================
    # Date Range Helpers
    # ============================================================

    @staticmethod
    def get_last_month_date_range():
        today = datetime.now()

        first_day_last_month = (today - relativedelta(months=1)).replace(day=1)
        start_date = first_day_last_month.replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        end_date = today.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

        return start_date, end_date

    # ============================================================
    # Filtering Helpers
    # ============================================================

    def _matches_exclude_pattern(self, project_path: str, exclude_patterns: List[str]):
        if not exclude_patterns:
            return False

        for pattern in exclude_patterns:
            if fnmatch.fnmatch(project_path, pattern):
                return True
            if fnmatch.fnmatch(project_path.split("/")[-1], pattern):
                return True

        return False

    # ============================================================
    # Commit Classification
    # ============================================================

    def _is_merge_commit(self, commit: Dict):
        msg = commit.get("message", "").lower()

        return (
            len(commit.get("parent_ids", [])) > 1
            or msg.startswith("merge")
            or "merge branch" in msg
            or "merged" in msg
        )

    def _is_rapid_commit(self, now_time, prev_time, window_minutes=5):
        if prev_time is None:
            return False

        diff = abs((now_time - prev_time).total_seconds() / 60)
        return diff <= window_minutes

    # ============================================================
    # ✅ Branch Filtering: Only Recent Branches
    # ============================================================
    def get_recent_branches(self, project, days: int = 90) -> List[str]:
        """
        Return branches updated in last N days.
        """

        # ✅ timezone-aware cutoff
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        recent = []
        branches = project.branches.list(all=True)

        print(f"Total branches: {len(branches)}")
        print(f"Cutoff date: {cutoff}")

        for b in branches:
            try:
                dt_str = b.commit["committed_date"]

                # ✅ timezone-aware last_commit
                last_commit = datetime.fromisoformat(
                    dt_str.replace("Z", "+00:00")
                )
                print(f"{b.name} {last_commit}, {cutoff} {last_commit >= cutoff}")
                if last_commit >= cutoff:
                    recent.append(b.name)

            except Exception as e:
                print(f"Error processing branch {b.name}: {e}")

        print(f"Recent branches found: {len(recent)}")
        return recent
     
    # ============================================================
    # ✅ Multi-Branch Commit Loader
    # ============================================================

    def get_project_commits_all_branches(
        self,
        project_id: int,
        start_date: datetime,
        end_date: datetime,
        recent_branch_days: int = 90,
    ) -> List[Dict]:

        commits = []
        seen_ids = set()

        project = self.gl.projects.get(project_id)

        # ✅ Recent branches only
        branch_names = self.get_recent_branches(
            project, days=recent_branch_days
        )

        print(f"    Active branches (last {recent_branch_days} days): {len(branch_names)}")

        since = start_date.isoformat()
        until = end_date.isoformat()

        for branch_name in branch_names:
            page = 1

            while True:
                commit_list = project.commits.list(
                    ref_name=branch_name,
                    since=since,
                    until=until,
                    per_page=100,
                    page=page,
                )

                if not commit_list:
                    break

                for c in commit_list:
                    if c.id in seen_ids:
                        continue

                    seen_ids.add(c.id)

                    full = project.commits.get(c.id)

                    commits.append(
                        {
                            "id": full.id,
                            "message": full.message,
                            "author_name": full.author_name,
                            "author_email": full.author_email,
                            "committed_date": full.committed_date,
                            "parent_ids": full.parent_ids,
                            "branch": branch_name,
                        }
                    )

                page += 1

        return commits

    # ============================================================
    # User Info Lookup
    # ============================================================

    def get_user_info(self, user_id: int):

        try:
            u = self.gl.users.get(user_id)
            return {
                "id": u.id,
                "name": u.name,
                "username": u.username,
                "email": u.email,
            }
        except:
            return None

    # ============================================================
    # ✅ Main Stats Collection
    # ============================================================

    def collect_commit_stats(
        self,
        start_date=None,
        end_date=None,
        exclude_patterns=None,
        groups_file="gitlab-groups.csv",
        rapid_window_minutes=5,
        recent_branch_days=90,
    ) -> List[CommitStats]:

        if start_date is None or end_date is None:
            start_date, end_date = self.get_last_month_date_range()

        exclude_patterns = exclude_patterns or []

        print(f"\nCollecting commits from {start_date.date()} → {end_date.date()}")
        print(f"Branches limited to last {recent_branch_days} days\n")

        all_projects = self.projects.get_all_projects_from_all_groups(groups_file)

        user_stats: Dict[int, CommitStats] = {}
        email_map: Dict[str, int] = {}

        for p in all_projects:

            pid = p.project_id
            path = p.project_path

            if self._matches_exclude_pattern(path, exclude_patterns):
                continue

            print(f"\nProject: {path} ({pid})")

            commits = self.get_project_commits_all_branches(
                pid,
                start_date,
                end_date,
                recent_branch_days=recent_branch_days,
            )

            print(f"  Total commits found: {len(commits)}")

            for commit in commits:

                email = commit.get("author_email")
                name = commit.get("author_name")

                if not email:
                    continue

                # Resolve user ID
                if email not in email_map:
                    users = self.gl.users.list(search=email)
                    if users:
                        email_map[email] = users[0].id
                    else:
                        email_map[email] = hash(email) % (10**9)

                uid = email_map[email]

                if uid not in user_stats:
                    info = self.get_user_info(uid)
                    user_stats[uid] = CommitStats(
                        user_id=uid,
                        user_full_name=info["name"] if info else name,
                        username=info["username"] if info else "",
                        email=email,
                    )

                stats = user_stats[uid]

                # Merge commit?
                if self._is_merge_commit(commit):
                    stats.merge_commits_count += 1
                else:
                    stats.commits_count += 1

                # Rapid commit detection
                if not hasattr(stats, "_last_commit_time"):
                    stats._last_commit_time = None

                dt = datetime.fromisoformat(
                    commit["committed_date"].replace("Z", "+00:00")
                )

                if self._is_rapid_commit(dt, stats._last_commit_time, rapid_window_minutes):
                    stats.has_rapid_commits = True
                    stats.rapid_commits_count += 1

                stats._last_commit_time = dt

        # Cleanup temp attribute
        for s in user_stats.values():
            if hasattr(s, "_last_commit_time"):
                delattr(s, "_last_commit_time")

        return list(user_stats.values())

    # ============================================================
    # CSV Export
    # ============================================================

    def save_stats_to_csv(self, stats: List[CommitStats], filepath="gitlab-commit-stats.csv"):

        if not stats:
            print("No stats collected.")
            return

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=stats[0].to_dict().keys())
            writer.writeheader()
            for s in stats:
                writer.writerow(s.to_dict())

        print(f"\nSaved results to: {filepath}")


# ============================================================
# Runner
# ============================================================

def generate_commit_stats(gitlab_url, token):

    collector = GitLabCommitStats(gitlab_url, token)

    stats = collector.collect_commit_stats(
        exclude_patterns=["infra*", "*infra-config*"],
        recent_branch_days=90,  # ✅ Only branches active in last 90 days
    )

    collector.save_stats_to_csv(stats)

    return stats


if __name__ == "__main__":

    GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")
    TOKEN = os.getenv("GITLAB_TOKEN")

    if not TOKEN:
        print("❌ Please set GITLAB_TOKEN environment variable")
        exit(1)

    generate_commit_stats(GITLAB_URL, TOKEN)
