"""
File utilities for code analysis.
Provides common functionality for finding and filtering files across analyzers.
"""
# Flake8: noqa: E501
import os
from typing import List, Set
from pathlib import Path


class CodebaseFileFilter:
    """
    Utility class for filtering files and directories during codebase scanning.
    Excludes virtual environments, package directories, and other non-source code.
    """

    def __init__(self):
        # Directories to exclude (virtual environments, packages, build artifacts)
        self.excluded_directories = {
            # Virtual environments
            "venv",
            ".venv",
            "env",
            ".env",
            "virtualenv",
            "pyvenv",
            ".pyvenv",
            "venv3",
            "venv2",
            # Python package directories
            "site-packages",
            "__pycache__",
            ".pytest_cache",
            "egg-info",
            ".eggs",
            "build",
            "dist",
            # Version control
            ".git",
            ".svn",
            ".hg",
            ".bzr",
            # IDE and editor directories
            ".vscode",
            ".idea",
            ".vs",
            "__pycache__",
            # Node.js (for mixed projects)
            "node_modules",
            # Other common exclusions
            ".mypy_cache",
            ".coverage",
            ".tox",
            ".nox",
            "htmlcov",
            "docs/_build",
            ".pytest_cache",
        }

        # File patterns to exclude
        self.excluded_file_patterns = {
            # Compiled Python
            "*.pyc",
            "*.pyo",
            "*.pyd",
            # Build artifacts
            "*.so",
            "*.dll",
            "*.dylib",
            # IDE files
            "*.swp",
            "*.swo",
            "*~",
        }

    def should_exclude_directory(self, dir_name: str, dir_path: str) -> bool:
        """
        Check if a directory should be excluded from scanning.

        Args:
            dir_name: Name of the directory
            dir_path: Full path to the directory

        Returns:
            True if directory should be excluded, False otherwise
        """
        # Check if directory name is in exclusion list
        if dir_name.lower() in self.excluded_directories:
            return True

        # Check for common virtual environment indicators
        if self._is_virtual_environment(dir_path):
            return True

        return False

    def _is_virtual_environment(self, dir_path: str) -> bool:
        """Check if directory appears to be a virtual environment."""
        path = Path(dir_path)

        # Look for common virtual environment structure
        indicators = [
            "pyvenv.cfg",  # Standard venv indicator
            "bin/activate",  # Unix venv
            "Scripts/activate.bat",  # Windows venv
            "lib/python",  # Python lib directory
            "include/python",  # Python include directory
        ]

        for indicator in indicators:
            if (path / indicator).exists():
                return True

        return False

    def find_python_files(
        self, target_path: str, exclude_test_files: bool = False
    ) -> List[str]:
        """
        Find all Python files in a path, excluding virtual environments and packages.

        Args:
            target_path: Path to scan (file or directory)
            exclude_test_files: Whether to exclude test files

        Returns:
            List of Python file paths
        """
        python_files = []

        if not os.path.exists(target_path):
            return python_files

        # Handle single file
        if os.path.isfile(target_path) and target_path.endswith(".py"):
            if exclude_test_files and self._is_test_file(target_path):
                return python_files
            python_files.append(target_path)
            return python_files

        # Handle directory
        if os.path.isdir(target_path):
            for root, dirs, files in os.walk(target_path):
                # Filter out excluded directories (modify dirs in-place to skip them)
                dirs[:] = [
                    d
                    for d in dirs
                    if not self.should_exclude_directory(d, os.path.join(root, d))
                ]

                # Process Python files in current directory
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)

                        # Skip test files if requested
                        if exclude_test_files and self._is_test_file(file_path):
                            continue

                        python_files.append(file_path)

        return python_files

    def _is_test_file(self, file_path: str) -> bool:
        """Check if a file is a test file based on naming patterns."""
        filename = os.path.basename(file_path).lower()
        return (
            filename.startswith("test_")
            or filename.endswith("_test.py")
            or "test" in filename
            or "/test" in file_path.lower()
        )

    def add_excluded_directory(self, directory: str):
        """Add a custom directory to the exclusion list."""
        self.excluded_directories.add(directory.lower())

    def remove_excluded_directory(self, directory: str):
        """Remove a directory from the exclusion list."""
        self.excluded_directories.discard(directory.lower())

    def get_excluded_directories(self) -> Set[str]:
        """Get the current set of excluded directories."""
        return self.excluded_directories.copy()


# Global instance for convenience
default_filter = CodebaseFileFilter()


def find_python_files(
    target_path: str,
    exclude_test_files: bool = False,
    custom_filter: CodebaseFileFilter = None,
) -> List[str]:
    """
    Convenience function to find Python files with filtering.

    Args:
        target_path: Path to scan
        exclude_test_files: Whether to exclude test files
        custom_filter: Custom filter instance (uses default if None)

    Returns:
        List of Python file paths
    """
    filter_instance = custom_filter or default_filter
    return filter_instance.find_python_files(target_path, exclude_test_files)
