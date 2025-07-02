#!/usr/bin/env python
# coding: utf-8
"""
Retrieve a list of local branches from a Git repository using GitStats API.

This script demonstrates how to use the /branches endpoint to get all branches
in a repository along with the current branch information.

Usage:
    python branches_example.py [--repo REPO_PATH] [--api-url URL] [--format FORMAT]

Examples:
    python branches_example.py
    python branches_example.py --repo /path/to/repo
    python branches_example.py --format table
    python branches_example.py --api-url http://localhost:8080
"""
import argparse
import json
import sys
from os import environ
from pathlib import Path
from typing import Optional, List

import requests
from requests import RequestException


class GitStatsClient:
    """Client for interacting with the GitStats API."""
    
    def __init__(self, api_url: str = "http://127.0.0.1:8000"):
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "GitStats-Client/1.0"
        })
    
    def set_repo_path(self, repo_path: str) -> dict:
        """Set the repository path in the API."""
        try:
            response = self.session.post(
                f"{self.api_url}/set_repo",
                params={"repo": repo_path},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RequestException(f"Failed to set repository path: {e}")
    
    def get_branches(self, repo_path: Optional[str] = None) -> dict:
        """Get branches list from the API."""
        try:
            # Set repo path if provided
            if repo_path:
                self.set_repo_path(repo_path)
            
            response = self.session.get(
                f"{self.api_url}/branches",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RequestException(f"Failed to get branches: {e}")
    
    def get_current_branch(self, repo_path: Optional[str] = None) -> dict:
        """Get current branch from the API."""
        try:
            # Set repo path if provided
            if repo_path:
                self.set_repo_path(repo_path)
            
            response = self.session.get(
                f"{self.api_url}/current_branch",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RequestException(f"Failed to get current branch: {e}")


def validate_repo_path(repo_path: str) -> Path:
    """Validate that the repository path exists and is a directory."""
    path = Path(repo_path).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"Repository path does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Repository path is not a directory: {path}")
    if not (path / ".git").exists():
        raise ValueError(f"Not a git repository (no .git directory found): {path}")
    return path


def format_branches_table(branches: List[str], current_branch: str) -> str:
    """Format branches as a nice table."""
    if not branches:
        return "No branches found."
    
    output = []
    output.append("🌿 Repository Branches")
    output.append("=" * 50)
    
    # Calculate max width for alignment
    max_width = max(len(branch) for branch in branches) if branches else 10
    header_width = max(max_width, 15)
    
    # Header
    output.append(f"{'Branch Name':<{header_width}} | Status")
    output.append("-" * (header_width + 10))
    
    # Sort branches with current branch first
    sorted_branches = sorted(branches)
    if current_branch and current_branch in sorted_branches:
        sorted_branches.remove(current_branch)
        sorted_branches.insert(0, current_branch)
    
    # Branch list
    for branch in sorted_branches:
        status = "📍 CURRENT" if branch == current_branch else "  "
        output.append(f"{branch:<{header_width}} | {status}")
    
    output.append("")
    output.append(f"Total branches: {len(branches)}")
    if current_branch:
        output.append(f"Current branch: {current_branch}")
    
    return "\n".join(output)


def format_branches_list(branches: List[str], current_branch: str) -> str:
    """Format branches as a simple list."""
    if not branches:
        return "No branches found."
    
    output = []
    output.append("🌿 Repository Branches")
    output.append("=" * 30)
    
    # Sort branches with current branch first
    sorted_branches = sorted(branches)
    if current_branch and current_branch in sorted_branches:
        sorted_branches.remove(current_branch)
        sorted_branches.insert(0, current_branch)
    
    for branch in sorted_branches:
        if branch == current_branch:
            output.append(f"📍 {branch} (current)")
        else:
            output.append(f"   {branch}")
    
    output.append("")
    output.append(f"Total: {len(branches)} branches")
    
    return "\n".join(output)


def format_output(response: dict, format_type: str = "summary", verbose: bool = False) -> str:
    """Format the API response for display."""
    output = []
    
    if response.get("STATUS_CODE") == 200:
        data = response.get("DATA", {})
        branches = data.get("branches", [])
        current_branch = data.get("branch", "")
        repo = data.get("repo", "unknown")
        
        if format_type == "table":
            output.append(f"📁 Repository: {repo}")
            output.append("")
            output.append(format_branches_table(branches, current_branch))
        elif format_type == "list":
            output.append(f"📁 Repository: {repo}")
            output.append("")
            output.append(format_branches_list(branches, current_branch))
        else:  # summary
            output.append("🌿 Branch Summary")
            output.append("=" * 40)
            output.append(f"Repository: {repo}")
            output.append(f"Current branch: {current_branch or '(none)'}")
            output.append(f"Total branches: {len(branches)}")
            
            if branches:
                output.append("\nBranches:")
                for branch in sorted(branches):
                    marker = "📍" if branch == current_branch else "  "
                    output.append(f"  {marker} {branch}")
        
        if verbose:
            output.append("\n" + "=" * 50)
            output.append("📋 Full API Response:")
            output.append(json.dumps(response, indent=2))
    else:
        # Error response
        output.append("❌ Error Response")
        output.append("=" * 50)
        output.append(json.dumps(response, indent=2))
    
    return "\n".join(output)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Get list of branches from GitStats API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                # Use default repo
  %(prog)s --repo /path/to/repo           # Use specific repository
  %(prog)s --format table                 # Display as table
  %(prog)s --format list                  # Display as simple list
  %(prog)s --api-url http://localhost:8080 # Use different API URL
  %(prog)s --current-only                 # Show only current branch info
        """
    )
    
    parser.add_argument(
        "--repo", "-r",
        type=str,
        help="Path to the git repository (default: $HOME/repos/gitstats)"
    )
    
    parser.add_argument(
        "--api-url", "-u",
        type=str,
        default="http://127.0.0.1:8000",
        help="GitStats API URL (default: http://127.0.0.1:8000)"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["summary", "table", "list"],
        default="summary",
        help="Output format (default: summary)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show full API response in addition to formatted output"
    )
    
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Output only raw JSON response"
    )
    
    parser.add_argument(
        "--current-only",
        action="store_true",
        help="Show only current branch information"
    )
    
    parser.add_argument(
        "--count-only",
        action="store_true",
        help="Show only the number of branches"
    )
    
    return parser.parse_args()


def main():
    """Main function."""
    try:
        args = parse_arguments()
        
        # Determine repository path
        repo_path = args.repo or f"{environ.get('HOME', '.')}/repos/gitstats"
        
        # Validate repository path if provided
        if repo_path:
            try:
                validated_path = validate_repo_path(repo_path)
                repo_path = str(validated_path)
            except ValueError as e:
                print(f"❌ Repository validation error: {e}", file=sys.stderr)
                sys.exit(1)
        
        # Create client
        client = GitStatsClient(args.api_url)
        
        print(f"🔍 Fetching branch information from {args.api_url}...")
        if repo_path:
            print(f"📁 Repository: {repo_path}")
        print()
        
        # Get appropriate data based on options
        if args.current_only:
            response = client.get_current_branch(repo_path)
            
            if args.json_only:
                print(json.dumps(response, indent=2))
            elif response.get("STATUS_CODE") == 200:
                data = response.get("DATA", {})
                current_branch = data.get("branch", "unknown")
                repo = data.get("repo", "unknown")
                print("📍 Current Branch Information")
                print("=" * 40)
                print(f"Repository: {repo}")
                print(f"Current branch: {current_branch}")
            else:
                print("❌ Failed to get current branch information")
                print(json.dumps(response, indent=2))
        else:
            response = client.get_branches(repo_path)
            
            if args.json_only:
                print(json.dumps(response, indent=2))
            elif args.count_only and response.get("STATUS_CODE") == 200:
                data = response.get("DATA", {})
                branches = data.get("branches", [])
                print(f"{len(branches)}")
            else:
                print(format_output(response, args.format, args.verbose))
        
        # Exit with appropriate code
        sys.exit(0 if response.get("STATUS_CODE") == 200 else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except RequestException as e:
        print(f"❌ API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()