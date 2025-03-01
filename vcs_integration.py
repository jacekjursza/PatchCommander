import os
import subprocess
from rich.console import Console
from rich.prompt import Prompt

console = Console()

class VCSIntegration:
    """
    Integration with version control systems (Git, Mercurial, SVN).
    """
    
    @staticmethod
    def detect_vcs(directory="."):
        """
        Detect which VCS is being used in the specified directory.
        
        Args:
            directory (str): Directory to check for VCS
            
        Returns:
            str: 'git', 'hg', 'svn', or None if no VCS detected
        """
        if os.path.exists(os.path.join(directory, ".git")):
            return "git"
        elif os.path.exists(os.path.join(directory, ".hg")):
            return "hg"
        elif os.path.exists(os.path.join(directory, ".svn")):
            return "svn"
        return None
    
    @staticmethod
    def _run_command(command, cwd=None):
        """
        Run a shell command and return output.
        
        Args:
            command (list): Command and arguments as list
            cwd (str): Working directory for the command
            
        Returns:
            tuple: (success_bool, output_str)
        """
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def get_modified_files():
        """
        Get list of modified files in the current VCS.
        
        Returns:
            list: List of modified file paths or empty list if error
        """
        vcs = VCSIntegration.detect_vcs()
        if not vcs:
            return []
            
        if vcs == "git":
            success, output = VCSIntegration._run_command(["git", "status", "--porcelain"])
            if success:
                files = []
                for line in output.split('\n'):
                    if line.strip():
                        status = line[:2]
                        filename = line[3:].strip()
                        # Only include modified, added, deleted files
                        if status in ["M ", " M", "A ", "D "]:
                            files.append(filename)
                return files
            return []
            
        elif vcs == "hg":
            success, output = VCSIntegration._run_command(["hg", "status"])
            if success:
                files = []
                for line in output.split('\n'):
                    if line.strip():
                        status = line[0]
                        filename = line[2:].strip()
                        # Only include modified, added, deleted files
                        if status in ["M", "A", "R"]:
                            files.append(filename)
                return files
            return []
            
        elif vcs == "svn":
            success, output = VCSIntegration._run_command(["svn", "status"])
            if success:
                files = []
                for line in output.split('\n'):
                    if line.strip():
                        status = line[0]
                        filename = line[8:].strip()
                        # Only include modified, added, deleted files
                        if status in ["M", "A", "D"]:
                            files.append(filename)
                return files
            return []
            
        return []
    
    @staticmethod
    def commit_changes(message, files=None):
        """
        Commit changes to the VCS.
        
        Args:
            message (str): Commit message
            files (list): List of files to commit. If None, commit all modified files.
            
        Returns:
            bool: True if commit succeeded, False otherwise
        """
        vcs = VCSIntegration.detect_vcs()
        if not vcs:
            console.print("[yellow]No version control system detected.[/yellow]")
            return False
        
        if vcs == "git":
            if files:
                # Add specific files
                command = ["git", "add"] + files
                success, output = VCSIntegration._run_command(command)
                if not success:
                    console.print(f"[red]Error adding files to git: {output}[/red]")
                    return False
            else:
                # Add all modified files
                success, output = VCSIntegration._run_command(["git", "add", "-A"])
                if not success:
                    console.print(f"[red]Error adding files to git: {output}[/red]")
                    return False
            
            # Commit changes
            success, output = VCSIntegration._run_command(["git", "commit", "-m", message])
            if success:
                console.print(f"[green]Successfully committed changes to git: {output}[/green]")
                return True
            else:
                console.print(f"[red]Error committing to git: {output}[/red]")
                return False
                
        elif vcs == "hg":
            commit_command = ["hg", "commit", "-m", message]
            if files:
                commit_command.extend(files)
            
            success, output = VCSIntegration._run_command(commit_command)
            if success:
                console.print(f"[green]Successfully committed changes to mercurial: {output}[/green]")
                return True
            else:
                console.print(f"[red]Error committing to mercurial: {output}[/red]")
                return False
                
        elif vcs == "svn":
            if files:
                # Add specific files (if they're not already tracked)
                for file in files:
                    VCSIntegration._run_command(["svn", "add", file, "--parents", "--force"])
                
                # Commit specific files
                success, output = VCSIntegration._run_command(["svn", "commit", "-m", message] + files)
            else:
                # Commit all changes
                success, output = VCSIntegration._run_command(["svn", "commit", "-m", message])
                
            if success:
                console.print(f"[green]Successfully committed changes to svn: {output}[/green]")
                return True
            else:
                console.print(f"[red]Error committing to svn: {output}[/red]")
                return False
                
        return False
    
    @staticmethod
    def create_branch(branch_name):
        """
        Create a new branch in the VCS.
        
        Args:
            branch_name (str): Name of the branch to create
            
        Returns:
            bool: True if branch creation succeeded, False otherwise
        """
        vcs = VCSIntegration.detect_vcs()
        if not vcs:
            console.print("[yellow]No version control system detected.[/yellow]")
            return False
            
        if vcs == "git":
            success, output = VCSIntegration._run_command(["git", "checkout", "-b", branch_name])
            if success:
                console.print(f"[green]Successfully created and switched to branch '{branch_name}'[/green]")
                return True
            else:
                console.print(f"[red]Error creating git branch: {output}[/red]")
                return False
                
        elif vcs == "hg":
            success, output = VCSIntegration._run_command(["hg", "branch", branch_name])
            if success:
                console.print(f"[green]Successfully created and switched to branch '{branch_name}'[/green]")
                return True
            else:
                console.print(f"[red]Error creating mercurial branch: {output}[/red]")
                return False
                
        elif vcs == "svn":
            # SVN doesn't have native branch switching, typically branches are directories
            console.print("[yellow]Branch creation in SVN requires repository layout knowledge and isn't supported automatically.[/yellow]")
            return False
            
        return False
