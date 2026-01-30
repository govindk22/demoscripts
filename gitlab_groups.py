import csv
import os
import fnmatch
import re
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
 
 
class GitLabGroupsLoader:
    """Manages GitLab group projects and CSV operations with per-group CSV files."""
    
    def __init__(self):
        """
        Loads gitload groups from local CSV file.
         
        """
       
    
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
                    exclude_patterns = [p.strip() for p in excludes.split(',') if p.strip()] if excludes else []
                    groups.append((group_path, exclude_patterns))
        
        return groups
    
     
     