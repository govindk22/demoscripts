import csv
import os
import fnmatch
import re
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
import gitlab


@dataclass
class GitLabProject:
    """Data class for GitLab project information."""
    project_id: int
    project_name: str
    project_path: str
    group_path: str
    repository_name: str
    web_url: str
    default_branch: str
    visibility: str
    status: str = "Current"
    last_updated: str = ""

    def to_dict(self) -> Dict:
        """Convert project to dictionary for CSV export."""
        return {
            'project_id': self.project_id,
            'project_name': self.project_name,
            'project_path': self.project_path,
            'group_path': self.group_path,
            'repository_name': self.repository_name,
            'web_url': self.web_url,
            'default_branch': self.default_branch,
            'visibility': self.visibility,
            'status': self.status,
            'last_updated': self.last_updated
        }


class GitLabProjectManager:
    """Manages GitLab group projects and CSV operations with per-group CSV files."""
    
    def __init__(self, gitlab_url: str, private_token: str, csv_prefix: str = 'gitlab-projects'):
        """
        Initialize GitLab project manager.
        
        Args:
            gitlab_url: GitLab instance URL (e.g., 'https://gitlab.com')
            private_token: GitLab private token with API access
            csv_prefix: Prefix for CSV files (default: 'gitlab-projects')
                        Files will be named: {prefix}-{group-path-sanitized}.csv
        """
        self.gitlab_url = gitlab_url
        self.private_token = private_token
        self.csv_prefix = csv_prefix
        self.gl = gitlab.Gitlab(gitlab_url, private_token=private_token)
        self.gl.auth()
    
    def _sanitize_group_path_for_filename(self, group_path: str) -> str:
        """
        Convert group path to a valid filename.
        
        Args:
            group_path: Group path (e.g., 'mycompany/team1')
            
        Returns:
            Sanitized filename-safe string (e.g., 'mycompany-team1')
        """
        # Replace slashes and other invalid filename characters with hyphens
        sanitized = re.sub(r'[<>:"/\\|?*]', '-', group_path)
        # Replace multiple hyphens with single hyphen
        sanitized = re.sub(r'-+', '-', sanitized)
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')
        return sanitized
    
    def _get_group_csv_filename(self, group_path: str) -> str:
        """
        Get CSV filename for a specific group.
        
        Args:
            group_path: Group path (e.g., 'mycompany/team1')
            
        Returns:
            CSV filename (e.g., 'gitlab-projects-mycompany-team1.csv')
        """
        sanitized = self._sanitize_group_path_for_filename(group_path)
        return f"{self.csv_prefix}-{sanitized}.csv"
    
    def load_groups_from_csv(self, groups_file: str = 'gitlab-groups.csv') -> List[Tuple[str, List[str]]]:
        """
        Load groups and their exclude patterns from CSV file.
        
        Args:
            groups_file: Path to groups CSV file
            
        Returns:
            List of tuples: (group_path, list_of_exclude_patterns)
        """
        groups = []
        if not os.path.exists(groups_file):
            print(f"Groups file {groups_file} does not exist.")
            return groups
        
        with open(groups_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                group_path = row.get('gitlab-group', '').strip()
                excludes = row.get('excludes', '').strip()
                
                if group_path:
                    # Parse exclude patterns (comma-separated)
                    exclude_patterns = [p.strip() for p in excludes.split(',') if p.strip()] if excludes else []
                    groups.append((group_path, exclude_patterns))
        
        return groups
    
    def _matches_exclude_pattern(self, project_path: str, exclude_patterns: List[str]) -> bool:
        """
        Check if project path matches any exclude pattern.
        
        Args:
            project_path: Full project path (e.g., 'mycompany/team1/project-name')
            exclude_patterns: List of wildcard patterns (e.g., ['infra*', '*poc*'])
            
        Returns:
            True if project should be excluded, False otherwise
        """
        if not exclude_patterns:
            return False
        
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(project_path, pattern) or fnmatch.fnmatch(project_path.split('/')[-1], pattern):
                return True
        return False
    
    def get_group_projects(self, group_path: str, exclude_patterns: List[str] = None) -> List[GitLabProject]:
        """
        Fetch all projects from a GitLab group (including subgroups).
        
        Args:
            group_path: Full path of the GitLab group (e.g., 'mycompany/team1')
            exclude_patterns: List of wildcard patterns to exclude
            
        Returns:
            List of GitLabProject objects
        """
        projects = []
        exclude_patterns = exclude_patterns or []
        
        try:
            group = self.gl.groups.get(group_path)
            
            # Get all projects including from subgroups
            for project in group.projects.list(all=True, include_subgroups=True):
                project_path = project.path_with_namespace
                
                # Check if project should be excluded
                if self._matches_exclude_pattern(project_path, exclude_patterns):
                    print(f"Excluding project: {project_path}")
                    continue
                
                try:
                    # Get full project details
                    full_project = self.gl.projects.get(project.id)
                    
                    project_obj = GitLabProject(
                        project_id=project.id,
                        project_name=project.name,
                        project_path=project_path,
                        group_path=group_path,
                        repository_name=project.name,
                        web_url=full_project.web_url or '',
                        default_branch=full_project.default_branch or '',
                        visibility=full_project.visibility or 'private',
                        status='Current',
                        last_updated=datetime.now().isoformat()
                    )
                    projects.append(project_obj)
                except Exception as e:
                    print(f"Warning: Could not fetch project details for ID {project.id}: {e}")
                    continue
        except gitlab.exceptions.GitlabGetError as e:
            print(f"Error fetching group '{group_path}': {e}")
        except Exception as e:
            print(f"Unexpected error fetching group '{group_path}': {e}")
        
        return projects
    
    def save_projects_to_csv(self, projects: List[GitLabProject], group_path: str, 
                            filepath: Optional[str] = None) -> None:
        """
        Save projects to CSV file for a specific group.
        
        Args:
            projects: List of GitLabProject objects to save
            group_path: Group path (used to generate filename if filepath not provided)
            filepath: Optional custom filepath (defaults to group-specific CSV file)
        """
        if filepath is None:
            filepath = self._get_group_csv_filename(group_path)
        
        if not projects:
            print(f"No projects to save for group {group_path}.")
            return
        
        fieldnames = ['project_id', 'project_name', 'project_path', 'group_path', 
                     'repository_name', 'web_url', 'default_branch', 'visibility', 
                     'status', 'last_updated']
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for project in projects:
                writer.writerow(project.to_dict())
        
        print(f"Saved {len(projects)} projects to {filepath}")
    
    def load_projects_from_csv(self, group_path: str, 
                               filepath: Optional[str] = None) -> List[GitLabProject]:
        """
        Load projects from CSV file for a specific group.
        
        Args:
            group_path: Group path (used to generate filename if filepath not provided)
            filepath: Optional custom filepath (defaults to group-specific CSV file)
            
        Returns:
            List of GitLabProject objects
        """
        if filepath is None:
            filepath = self._get_group_csv_filename(group_path)
        
        if not os.path.exists(filepath):
            print(f"CSV file {filepath} does not exist for group {group_path}.")
            return []
        
        projects = []
        with open(filepath, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                project = GitLabProject(
                    project_id=int(row['project_id']),
                    project_name=row['project_name'],
                    project_path=row['project_path'],
                    group_path=row['group_path'],
                    repository_name=row.get('repository_name', row['project_name']),
                    web_url=row.get('web_url', ''),
                    default_branch=row.get('default_branch', ''),
                    visibility=row.get('visibility', 'private'),
                    status=row.get('status', 'Current'),
                    last_updated=row.get('last_updated', '')
                )
                projects.append(project)
        
        print(f"Loaded {len(projects)} projects from {filepath}")
        return projects
    
    def update_csv_with_changes(self, new_projects: List[GitLabProject], 
                                group_path: str,
                                filepath: Optional[str] = None) -> Dict[str, int]:
        """
        Update CSV file with new project data for a specific group, tracking changes (Added, Deleted, etc.).
        
        Args:
            new_projects: List of current GitLabProject objects
            group_path: Group path
            filepath: Optional custom filepath (defaults to group-specific CSV file)
            
        Returns:
            Dictionary with counts of changes: {'Added': count, 'Deleted': count, 'Updated': count}
        """
        if filepath is None:
            filepath = self._get_group_csv_filename(group_path)
        
        # Load existing projects
        existing_projects = self.load_projects_from_csv(group_path, filepath)
        
        # Create lookup dictionaries - key by project_id
        existing_dict = {p.project_id: p for p in existing_projects}
        new_dict = {p.project_id: p for p in new_projects}
        
        # Find added, deleted, and updated projects
        existing_keys = set(existing_dict.keys())
        new_keys = set(new_dict.keys())
        
        added_keys = new_keys - existing_keys
        deleted_keys = existing_keys - new_keys
        updated_keys = existing_keys & new_keys
        
        # Mark new projects as Added
        for key in added_keys:
            new_dict[key].status = 'Added'
            new_dict[key].last_updated = datetime.now().isoformat()
        
        # Mark deleted projects
        deleted_projects = []
        for key in deleted_keys:
            project = existing_dict[key]
            project.status = 'Deleted'
            project.last_updated = datetime.now().isoformat()
            deleted_projects.append(project)
        
        # Check for updates (e.g., name changes, visibility changes)
        updated_count = 0
        for key in updated_keys:
            existing = existing_dict[key]
            new = new_dict[key]
            
            # Check if any relevant fields changed
            if (existing.project_name != new.project_name or 
                existing.project_path != new.project_path or
                existing.group_path != new.group_path or
                existing.visibility != new.visibility or
                existing.default_branch != new.default_branch):
                new.status = 'Updated'
                new.last_updated = datetime.now().isoformat()
                updated_count += 1
            else:
                # Keep existing status if it was Added/Deleted, otherwise Current
                if existing.status not in ['Added', 'Deleted']:
                    new.status = 'Current'
                else:
                    new.status = existing.status
                new.last_updated = existing.last_updated
        
        # Combine all projects: current + deleted
        all_projects = list(new_dict.values()) + deleted_projects
        
        # Save updated CSV
        self.save_projects_to_csv(all_projects, group_path, filepath)
        
        stats = {
            'Added': len(added_keys),
            'Deleted': len(deleted_keys),
            'Updated': updated_count,
            'Current': len([p for p in all_projects if p.status == 'Current'])
        }
        
        print(f"Update complete for {group_path}: {stats}")
        return stats
    
    def refresh_group_projects(self, group_path: str, exclude_patterns: List[str] = None,
                             track_changes: bool = True) -> Dict[str, int]:
        """
        Refresh projects for a specific group and update CSV with change tracking.
        
        Args:
            group_path: Group path to refresh
            exclude_patterns: List of wildcard patterns to exclude
            track_changes: Whether to track changes (Added/Updated/Deleted)
            
        Returns:
            Dictionary with counts of changes if track_changes=True, else empty dict
        """
        print(f"Refreshing projects for group: {group_path}")
        new_projects = self.get_group_projects(group_path, exclude_patterns)
        
        if track_changes:
            stats = self.update_csv_with_changes(new_projects, group_path)
            return stats
        else:
            self.save_projects_to_csv(new_projects, group_path)
            return {}
    
    def refresh_all_groups_projects(self, groups_file: str = 'gitlab-groups.csv', 
                                   track_changes: bool = True) -> Dict[str, Dict[str, int]]:
        """
        Refresh projects from all groups listed in groups CSV file.
        Each group's projects are saved to a separate CSV file.
        
        Args:
            groups_file: Path to groups CSV file
            track_changes: Whether to track changes (Added/Updated/Deleted)
            
        Returns:
            Dictionary mapping group_path to statistics dict
        """
        groups = self.load_groups_from_csv(groups_file)
        all_stats = {}
        
        for group_path, exclude_patterns in groups:
            stats = self.refresh_group_projects(group_path, exclude_patterns, track_changes)
            all_stats[group_path] = stats
        
        return all_stats
    
    def get_projects_by_group(self, group_path: str, 
                            filepath: Optional[str] = None) -> List[GitLabProject]:
        """
        Load and return projects for a specific group from CSV.
        
        Args:
            group_path: Group path
            filepath: Optional custom filepath (defaults to group-specific CSV file)
            
        Returns:
            List of GitLabProject objects for the specified group
        """
        return self.load_projects_from_csv(group_path, filepath)
    
    def get_projects_by_status(self, group_path: str, status: str,
                             filepath: Optional[str] = None) -> List[GitLabProject]:
        """
        Load and filter projects by status from CSV for a specific group.
        
        Args:
            group_path: Group path
            status: Status to filter by (e.g., 'Added', 'Deleted', 'Current')
            filepath: Optional custom filepath (defaults to group-specific CSV file)
            
        Returns:
            List of GitLabProject objects with the specified status
        """
        all_projects = self.load_projects_from_csv(group_path, filepath)
        return [p for p in all_projects if p.status == status]
    
    def get_all_projects_from_all_groups(self, groups_file: str = 'gitlab-groups.csv') -> List[GitLabProject]:
        """
        Load projects from all group CSV files.
        
        Args:
            groups_file: Path to groups CSV file
            
        Returns:
            List of all GitLabProject objects from all groups
        """
        groups = self.load_groups_from_csv(groups_file)
        all_projects = []
        
        for group_path, _ in groups:
            projects = self.load_projects_from_csv(group_path)
            all_projects.extend(projects)
        
        return all_projects


# Convenience functions for use in other modules
def load_projects_from_csv(group_path: str, csv_prefix: str = 'gitlab-projects') -> List[Dict]:
    """
    Load projects from CSV file for a specific group for use in other modules.
    
    Args:
        group_path: Group path
        csv_prefix: Prefix for CSV files (default: 'gitlab-projects')
        
    Returns:
        List of dictionaries containing project data
    """
    manager = GitLabProjectManager('', '', csv_prefix)  # Dummy instance for loading only
    projects = manager.load_projects_from_csv(group_path)
    return [project.to_dict() for project in projects]


def get_projects_by_group(group_path: str, csv_prefix: str = 'gitlab-projects') -> List[Dict]:
    """
    Get projects for a specific group from CSV.
    
    Args:
        group_path: Group path to filter by
        csv_prefix: Prefix for CSV files (default: 'gitlab-projects')
        
    Returns:
        List of dictionaries containing project data for the group
    """
    manager = GitLabProjectManager('', '', csv_prefix)
    projects = manager.get_projects_by_group(group_path)
    return [project.to_dict() for project in projects]


def get_projects_by_status(group_path: str, status: str, 
                           csv_prefix: str = 'gitlab-projects') -> List[Dict]:
    """
    Get projects by status from CSV for a specific group.
    
    Args:
        group_path: Group path
        status: Status to filter by
        csv_prefix: Prefix for CSV files (default: 'gitlab-projects')
        
    Returns:
        List of dictionaries containing project data with the specified status
    """
    manager = GitLabProjectManager('', '', csv_prefix)
    projects = manager.get_projects_by_status(group_path, status)
    return [project.to_dict() for project in projects]


def get_project_by_id(project_id: int, groups_file: str = 'gitlab-groups.csv',
                      csv_prefix: str = 'gitlab-projects') -> Optional[Dict]:
    """
    Get a specific project by ID from any group CSV file.
    
    Args:
        project_id: Project ID to find
        groups_file: Path to groups CSV file
        csv_prefix: Prefix for CSV files (default: 'gitlab-projects')
        
    Returns:
        Dictionary containing project data, or None if not found
    """
    manager = GitLabProjectManager('', '', csv_prefix)
    all_projects = manager.get_all_projects_from_all_groups(groups_file)
    
    for project in all_projects:
        if project.project_id == project_id:
            return project.to_dict()
    return None


def get_all_projects_from_all_groups(groups_file: str = 'gitlab-groups.csv',
                                     csv_prefix: str = 'gitlab-projects') -> List[Dict]:
    """
    Load all projects from all group CSV files.
    
    Args:
        groups_file: Path to groups CSV file
        csv_prefix: Prefix for CSV files (default: 'gitlab-projects')
        
    Returns:
        List of dictionaries containing all project data from all groups
    """
    manager = GitLabProjectManager('', '', csv_prefix)
    projects = manager.get_all_projects_from_all_groups(groups_file)
    return [project.to_dict() for project in projects]


# Example usage
if __name__ == '__main__':
    # Configuration
    GITLAB_URL = os.getenv('GITLAB_URL', 'https://gitlab.com')
    GITLAB_TOKEN = os.getenv('GITLAB_TOKEN', '')
    CSV_PREFIX = 'gitlab-projects'
    GROUPS_FILE = 'gitlab-groups.csv'
    
    # Example: Refresh projects from all groups (each group gets its own CSV file)
    if GITLAB_TOKEN:
        manager = GitLabProjectManager(GITLAB_URL, GITLAB_TOKEN, CSV_PREFIX)
        
        # Refresh all groups - each group will have its own CSV file
        # e.g., gitlab-projects-mycompany-team1.csv, gitlab-projects-mycompany-team2.csv
        all_stats = manager.refresh_all_groups_projects(GROUPS_FILE, track_changes=True)
        
        for group_path, stats in all_stats.items():
            print(f"Group {group_path}: {stats}")
        
        # Or refresh a single group
        # stats = manager.refresh_group_projects('mycompany/team1', track_changes=True)
        
        # Example: Load projects for a specific group in another module
        # from gitlab_projects import load_projects_from_csv
        # team1_projects = load_projects_from_csv('mycompany/team1')
        
        # Example: Get all projects from all groups
        # from gitlab_projects import get_all_projects_from_all_groups
        # all_projects = get_all_projects_from_all_groups()
    else:
        print("Please set GITLAB_TOKEN environment variable")