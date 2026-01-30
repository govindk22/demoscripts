import csv
import os
from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
import gitlab

@dataclass
class GitLabMember:
    """Data class for GitLab member information."""
    member_id: int
    user_id: int
    full_name: str
    email: str
    username: str
    group_path: str
    access_level: str
    status: str = "Current"
    last_updated: str = ""

    def to_dict(self) -> Dict:
        """Convert member to dictionary for CSV export."""
        return {
            'member_id': self.member_id,
            'user_id': self.user_id,
            'full_name': self.full_name,
            'email': self.email,
            'username': self.username,
            'group_path': self.group_path,
            'access_level': self.access_level,
            'status': self.status,
            'last_updated': self.last_updated
        }


class GitLabMemberManager:
    """Manages GitLab group members and CSV operations."""
    
    def __init__(self, gitlab_url: str, private_token: str, csv_file: str = 'gitlab-members.csv'):
        """
        Initialize GitLab member manager.
        
        Args:
            gitlab_url: GitLab instance URL (e.g., 'https://gitlab.com')
            private_token: GitLab private token with API access
            csv_file: Path to CSV file for storing member data
        """
        self.gitlab_url = gitlab_url
        self.private_token = private_token
        self.csv_file = csv_file
        self.gl = gitlab.Gitlab(gitlab_url, private_token=private_token)
        self.gl.auth()
    
    def get_group_members(self, group_path: str) -> List[GitLabMember]:
        """
        Fetch all direct members of a GitLab group.
        
        Args:
            group_path: Full path of the GitLab group (e.g., 'mycompany/team1')
            
        Returns:
            List of GitLabMember objects
        """
        members = []
        try:
            group = self.gl.groups.get(group_path)
            
            # Get direct members only (not inherited)
            for member in group.members.list(all=True):
                try:
                    user = self.gl.users.get(member.id)
                    member_obj = GitLabMember(
                        member_id=member.id,
                        user_id=user.id,
                        full_name=user.name or '',
                        email= "test", #user.email if user.email else '',
                        username=user.username or '',
                        group_path=group_path,
                        access_level=self._get_access_level_name(member.access_level),
                        status='Current',
                        last_updated=datetime.now().isoformat()
                    )
                    members.append(member_obj)
                except Exception as e:
                    print(f"Warning: Could not fetch user details for member ID {member.id}: {e}")
                    continue
        except gitlab.exceptions.GitlabGetError as e:
            print(f"Error fetching group '{group_path}': {e}")
        except Exception as e:
            print(f"Unexpected error fetching group '{group_path}': {e}")
        
        return members
    
    def _get_access_level_name(self, access_level: int) -> str:
        """Convert access level number to name."""
        access_levels = {
            10: 'Guest',
            20: 'Reporter',
            30: 'Developer',
            40: 'Maintainer',
            50: 'Owner'
        }
        return access_levels.get(access_level, f'Unknown({access_level})')
    
    def get_all_groups_members(self, group_paths: List[str]) -> List[GitLabMember]:
        """
        Fetch members from multiple GitLab groups.
        
        Args:
            group_paths: List of group paths to fetch members from
            
        Returns:
            List of all GitLabMember objects from all groups
        """
        all_members = []
        for group_path in group_paths:
            print(f"Fetching members from group: {group_path}")
            members = self.get_group_members(group_path)
            all_members.extend(members)
            print(f"Found {len(members)} members in {group_path}")
        
        return all_members
    
    def save_members_to_csv(self, members: List[GitLabMember], filepath: Optional[str] = None) -> None:
        """
        Save members to CSV file.
        
        Args:
            members: List of GitLabMember objects to save
            filepath: Optional custom filepath (defaults to self.csv_file)
        """
        filepath = filepath or self.csv_file
        
        if not members:
            print("No members to save.")
            return
        
        fieldnames = ['member_id', 'user_id', 'full_name', 'email', 'username', 
                     'group_path', 'access_level', 'status', 'last_updated']
        
        file_exists = os.path.exists(filepath)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for member in members:
                writer.writerow(member.to_dict())
        
        print(f"Saved {len(members)} members to {filepath}")
    
    def load_members_from_csv(self, filepath: Optional[str] = None) -> List[GitLabMember]:
        """
        Load members from CSV file.
        
        Args:
            filepath: Optional custom filepath (defaults to self.csv_file)
            
        Returns:
            List of GitLabMember objects
        """
        filepath = filepath or self.csv_file
        
        if not os.path.exists(filepath):
            print(f"CSV file {filepath} does not exist.")
            return []
        
        members = []
        with open(filepath, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                member = GitLabMember(
                    member_id=int(row['member_id']),
                    user_id=int(row['user_id']),
                    full_name=row['full_name'],
                    email=row.get('email'),
                    username=row.get('username', ''),
                    group_path=row['group_path'],
                    access_level=row.get('access_level', ''),
                    status=row.get('status', 'Current'),
                    last_updated=row.get('last_updated', '')
                )
                members.append(member)
        
        print(f"Loaded {len(members)} members from {filepath}")
        return members
    
    def update_csv_with_changes(self, new_members: List[GitLabMember], 
                                filepath: Optional[str] = None) -> Dict[str, int]:
        """
        Update CSV file with new member data, tracking changes (Added, Deleted, etc.).
        
        Args:
            new_members: List of current GitLabMember objects
            filepath: Optional custom filepath (defaults to self.csv_file)
            
        Returns:
            Dictionary with counts of changes: {'Added': count, 'Deleted': count, 'Updated': count}
        """
        filepath = filepath or self.csv_file
        
        # Load existing members
        existing_members = self.load_members_from_csv(filepath)
        
        # Create lookup dictionaries
        # Key: (user_id, group_path) to handle same user in multiple groups
        existing_dict = {(m.user_id, m.group_path): m for m in existing_members}
        new_dict = {(m.user_id, m.group_path): m for m in new_members}
        
        # Find added, deleted, and updated members
        existing_keys = set(existing_dict.keys())
        new_keys = set(new_dict.keys())
        
        added_keys = new_keys - existing_keys
        deleted_keys = existing_keys - new_keys
        updated_keys = existing_keys & new_keys
        
        # Mark new members as Added
        for key in added_keys:
            new_dict[key].status = 'Added'
            new_dict[key].last_updated = datetime.now().isoformat()
        
        # Mark deleted members
        deleted_members = []
        for key in deleted_keys:
            member = existing_dict[key]
            member.status = 'Deleted'
            member.last_updated = datetime.now().isoformat()
            deleted_members.append(member)
        
        # Check for updates (e.g., access level changes)
        updated_count = 0
        for key in updated_keys:
            existing = existing_dict[key]
            new = new_dict[key]
            
            # Check if any relevant fields changed
            if (existing.access_level != new.access_level or 
                existing.full_name != new.full_name or 
                existing.email != new.email):
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
        
        # Combine all members: current + deleted
        all_members = list(new_dict.values()) + deleted_members
        
        # Save updated CSV
        self.save_members_to_csv(all_members, filepath)
        
        stats = {
            'Added': len(added_keys),
            'Deleted': len(deleted_keys),
            'Updated': updated_count,
            'Current': len([m for m in all_members if m.status == 'Current'])
        }
        
        print(f"Update complete: {stats}")
        return stats
    
    def get_members_by_group(self, group_path: str, 
                            filepath: Optional[str] = None) -> List[GitLabMember]:
        """
        Load and filter members by group path from CSV.
        
        Args:
            group_path: Group path to filter by
            filepath: Optional custom filepath (defaults to self.csv_file)
            
        Returns:
            List of GitLabMember objects for the specified group
        """
        all_members = self.load_members_from_csv(filepath)
        return [m for m in all_members if m.group_path == group_path]
    
    def get_members_by_status(self, status: str, 
                             filepath: Optional[str] = None) -> List[GitLabMember]:
        """
        Load and filter members by status from CSV.
        
        Args:
            status: Status to filter by (e.g., 'Added', 'Deleted', 'Current')
            filepath: Optional custom filepath (defaults to self.csv_file)
            
        Returns:
            List of GitLabMember objects with the specified status
        """
        all_members = self.load_members_from_csv(filepath)
        return [m for m in all_members if m.status == status]


# Convenience functions for use in other modules
def load_members_from_csv(csv_file: str = 'gitlab-members.csv') -> List[Dict]:
    """
    Load members from CSV file for use in other modules.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        List of dictionaries containing member data
    """
    manager = GitLabMemberManager('', '')  # Dummy instance for loading only
    members = manager.load_members_from_csv(csv_file)
    return [member.to_dict() for member in members]


def get_members_by_group(group_path: str, csv_file: str = 'gitlab-members.csv') -> List[Dict]:
    """
    Get members for a specific group from CSV.
    
    Args:
        group_path: Group path to filter by
        csv_file: Path to CSV file
        
    Returns:
        List of dictionaries containing member data for the group
    """
    manager = GitLabMemberManager('', '')
    members = manager.get_members_by_group(group_path, csv_file)
    return [member.to_dict() for member in members]


def get_members_by_status(status: str, csv_file: str = 'gitlab-members.csv') -> List[Dict]:
    """
    Get members by status from CSV.
    
    Args:
        status: Status to filter by
        csv_file: Path to CSV file
        
    Returns:
        List of dictionaries containing member data with the specified status
    """
    manager = GitLabMemberManager('', '')
    members = manager.get_members_by_status(status, csv_file)
    return [member.to_dict() for member in members]


# Example usage
if __name__ == '__main__':
    # Configuration
    GITLAB_URL = os.getenv('GITLAB_URL', 'https://gitlab.com')
    GITLAB_TOKEN = os.getenv('GITLAB_TOKEN', '')
    CSV_FILE = 'gitlab-members.csv'
    
    # Example: Fetch members from groups
    if GITLAB_TOKEN:
        manager = GitLabMemberManager(GITLAB_URL, GITLAB_TOKEN, CSV_FILE)

      #  group_loader = GitLabGroupsLoader()

       # groups = group_loader.load_groups_from_csv()

       # select gitlab-group from groups
        
        # Example: Fetch from specific groups
        group_paths = ['gk-poc-team01']
        members = manager.get_all_groups_members(group_paths)
        
        # Save initial CSV
        manager.save_members_to_csv(members)
        
        # Or update with change tracking
        # stats = manager.update_csv_with_changes(members)
        
        # Example: Load members in another module
        # from gitlab_member import load_members_from_csv
        # all_members = load_members_from_csv(CSV_FILE)
    else:
        print("Please set GITLAB_TOKEN environment variable")