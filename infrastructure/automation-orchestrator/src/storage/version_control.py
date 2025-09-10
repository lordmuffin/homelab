"""
Git version control integration for asset storage.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess

from ..core.logger import get_logger

logger = get_logger(__name__)


class GitVersionControl:
    """Git version control integration for tracking asset changes."""
    
    def __init__(self, repository_path: Path):
        """
        Initialize Git version control.
        
        Args:
            repository_path: Path to git repository
        """
        self.repo_path = Path(repository_path)
        self.logger = get_logger(f"{__name__}.GitVersionControl")
        
        # Ensure repository path exists
        self.repo_path.mkdir(parents=True, exist_ok=True)
    
    async def initialize_repository(self) -> bool:
        """
        Initialize git repository if it doesn't exist.
        
        Returns:
            True if repository initialized or already exists
        """
        try:
            git_dir = self.repo_path / ".git"
            
            if not git_dir.exists():
                # Initialize new repository
                result = await self._run_git_command(['init'])
                if result.returncode != 0:
                    self.logger.error(f"Failed to initialize git repository: {result.stderr}")
                    return False
                
                # Set up initial configuration
                await self._setup_initial_config()
                
                # Create initial commit
                await self._create_initial_commit()
                
                self.logger.info("Git repository initialized")
            else:
                self.logger.debug("Git repository already exists")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize git repository: {e}")
            return False
    
    async def _setup_initial_config(self):
        """Set up initial git configuration."""
        try:
            # Set user name and email for commits
            config_commands = [
                ['config', 'user.name', 'Automation Orchestrator'],
                ['config', 'user.email', 'orchestrator@homelab.local'],
                ['config', 'init.defaultBranch', 'main']
            ]
            
            for command in config_commands:
                await self._run_git_command(command)
            
            # Create .gitignore
            gitignore_content = """# Automation Orchestrator
*.pyc
__pycache__/
*.log
*.tmp
.DS_Store
Thumbs.db

# Compressed files (kept as backups)
*.gz

# Sensitive data (if any)
**/credentials/
**/secrets/
"""
            
            gitignore_file = self.repo_path / ".gitignore"
            with open(gitignore_file, 'w') as f:
                f.write(gitignore_content)
            
        except Exception as e:
            self.logger.warning(f"Failed to setup git config: {e}")
    
    async def _create_initial_commit(self):
        """Create initial commit."""
        try:
            # Add .gitignore
            await self._run_git_command(['add', '.gitignore'])
            
            # Create initial commit
            await self._run_git_command([
                'commit', '-m', 'Initial commit: Automation Orchestrator asset storage'
            ])
            
        except Exception as e:
            self.logger.warning(f"Failed to create initial commit: {e}")
    
    async def commit_changes(self, message: str, files: Optional[List[str]] = None) -> bool:
        """
        Commit changes to the repository.
        
        Args:
            message: Commit message
            files: Optional list of specific files to commit. If None, commits all changes.
            
        Returns:
            True if commit successful
        """
        try:
            # Check if there are changes to commit
            status_result = await self._run_git_command(['status', '--porcelain'])
            if not status_result.stdout.strip():
                self.logger.debug("No changes to commit")
                return True
            
            # Add files
            if files:
                for file in files:
                    await self._run_git_command(['add', file])
            else:
                await self._run_git_command(['add', '.'])
            
            # Create commit with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"{message}\n\nTimestamp: {timestamp}"
            
            result = await self._run_git_command(['commit', '-m', commit_message])
            
            if result.returncode == 0:
                self.logger.debug(f"Successfully committed changes: {message}")
                return True
            else:
                self.logger.warning(f"Git commit failed: {result.stderr}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to commit changes: {e}")
            return False
    
    async def get_commit_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get commit history.
        
        Args:
            limit: Maximum number of commits to return
            
        Returns:
            List of commit information dictionaries
        """
        try:
            # Get commit log
            result = await self._run_git_command([
                'log', '--oneline', '--decorate', f'-{limit}', '--pretty=format:%H|%an|%ad|%s'
            ])
            
            if result.returncode != 0:
                return []
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 3)
                    if len(parts) >= 4:
                        commits.append({
                            'hash': parts[0],
                            'author': parts[1],
                            'date': parts[2],
                            'message': parts[3]
                        })
            
            return commits
            
        except Exception as e:
            self.logger.error(f"Failed to get commit history: {e}")
            return []
    
    async def get_file_changes(self, file_path: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get change history for a specific file.
        
        Args:
            file_path: Path to file (relative to repository root)
            limit: Maximum number of changes to return
            
        Returns:
            List of file change information
        """
        try:
            result = await self._run_git_command([
                'log', '--oneline', f'-{limit}', '--pretty=format:%H|%an|%ad|%s', '--', file_path
            ])
            
            if result.returncode != 0:
                return []
            
            changes = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 3)
                    if len(parts) >= 4:
                        changes.append({
                            'hash': parts[0],
                            'author': parts[1],
                            'date': parts[2],
                            'message': parts[3],
                            'file': file_path
                        })
            
            return changes
            
        except Exception as e:
            self.logger.error(f"Failed to get file changes for {file_path}: {e}")
            return []
    
    async def get_repository_status(self) -> Dict[str, Any]:
        """
        Get current repository status.
        
        Returns:
            Repository status dictionary
        """
        try:
            status = {
                'has_changes': False,
                'untracked_files': [],
                'modified_files': [],
                'staged_files': [],
                'current_branch': 'unknown',
                'last_commit': None,
                'total_commits': 0
            }
            
            # Get status
            result = await self._run_git_command(['status', '--porcelain'])
            if result.returncode == 0:
                status_lines = result.stdout.strip().split('\n')
                for line in status_lines:
                    if line:
                        status['has_changes'] = True
                        status_code = line[:2]
                        filename = line[3:]
                        
                        if status_code == '??':
                            status['untracked_files'].append(filename)
                        elif status_code[0] in ['M', 'A', 'D']:
                            status['staged_files'].append(filename)
                        elif status_code[1] in ['M', 'A', 'D']:
                            status['modified_files'].append(filename)
            
            # Get current branch
            result = await self._run_git_command(['branch', '--show-current'])
            if result.returncode == 0:
                status['current_branch'] = result.stdout.strip()
            
            # Get last commit info
            result = await self._run_git_command(['log', '-1', '--pretty=format:%H|%an|%ad|%s'])
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split('|', 3)
                if len(parts) >= 4:
                    status['last_commit'] = {
                        'hash': parts[0],
                        'author': parts[1],
                        'date': parts[2],
                        'message': parts[3]
                    }
            
            # Get total commits
            result = await self._run_git_command(['rev-list', '--count', 'HEAD'])
            if result.returncode == 0 and result.stdout.strip():
                try:
                    status['total_commits'] = int(result.stdout.strip())
                except ValueError:
                    pass
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get repository status: {e}")
            return {'error': str(e)}
    
    async def create_tag(self, tag_name: str, message: str) -> bool:
        """
        Create a git tag.
        
        Args:
            tag_name: Name of the tag
            message: Tag message
            
        Returns:
            True if tag created successfully
        """
        try:
            result = await self._run_git_command(['tag', '-a', tag_name, '-m', message])
            
            if result.returncode == 0:
                self.logger.info(f"Created tag: {tag_name}")
                return True
            else:
                self.logger.warning(f"Failed to create tag {tag_name}: {result.stderr}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to create tag {tag_name}: {e}")
            return False
    
    async def list_tags(self) -> List[str]:
        """
        List all tags in the repository.
        
        Returns:
            List of tag names
        """
        try:
            result = await self._run_git_command(['tag', '--list'])
            
            if result.returncode == 0:
                tags = [tag.strip() for tag in result.stdout.split('\n') if tag.strip()]
                return tags
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to list tags: {e}")
            return []
    
    async def create_branch(self, branch_name: str) -> bool:
        """
        Create a new branch.
        
        Args:
            branch_name: Name of the new branch
            
        Returns:
            True if branch created successfully
        """
        try:
            result = await self._run_git_command(['checkout', '-b', branch_name])
            
            if result.returncode == 0:
                self.logger.info(f"Created and switched to branch: {branch_name}")
                return True
            else:
                self.logger.warning(f"Failed to create branch {branch_name}: {result.stderr}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to create branch {branch_name}: {e}")
            return False
    
    async def switch_branch(self, branch_name: str) -> bool:
        """
        Switch to existing branch.
        
        Args:
            branch_name: Name of the branch to switch to
            
        Returns:
            True if switched successfully
        """
        try:
            result = await self._run_git_command(['checkout', branch_name])
            
            if result.returncode == 0:
                self.logger.info(f"Switched to branch: {branch_name}")
                return True
            else:
                self.logger.warning(f"Failed to switch to branch {branch_name}: {result.stderr}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to switch to branch {branch_name}: {e}")
            return False
    
    async def _run_git_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """
        Run a git command asynchronously.
        
        Args:
            args: Git command arguments
            
        Returns:
            Completed process result
        """
        command = ['git'] + args
        
        try:
            # Run git command
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=self.repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = await process.communicate()
            
            return subprocess.CompletedProcess(
                args=command,
                returncode=process.returncode,
                stdout=stdout,
                stderr=stderr
            )
            
        except Exception as e:
            self.logger.error(f"Git command failed: {' '.join(command)}: {e}")
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout="",
                stderr=str(e)
            )
    
    async def is_repository_clean(self) -> bool:
        """
        Check if repository has no uncommitted changes.
        
        Returns:
            True if repository is clean
        """
        try:
            result = await self._run_git_command(['status', '--porcelain'])
            return result.returncode == 0 and not result.stdout.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to check repository status: {e}")
            return False
    
    async def get_diff(self, file_path: Optional[str] = None) -> str:
        """
        Get diff of changes.
        
        Args:
            file_path: Optional specific file to get diff for
            
        Returns:
            Diff output
        """
        try:
            args = ['diff']
            if file_path:
                args.append(file_path)
            
            result = await self._run_git_command(args)
            return result.stdout if result.returncode == 0 else ""
            
        except Exception as e:
            self.logger.error(f"Failed to get diff: {e}")
            return ""