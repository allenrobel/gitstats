#!/usr/bin/env python
# coding: utf-8
"""
Retrieve the total number of commits from a Git repository using GitStats API.

This script demonstrates how to use the /commit_count endpoint to retrieve commit
statistics for a repository branch. It supports both current branch and specific
branch queries.

Usage:
    python commit_count_example.py [--branch BRANCH_NAME] [--repo REPO_PATH] [--api-url URL]

Examples:
    python commit_count_example.py
    python commit_count_example.py --branch main
    python commit_count_example.py --repo /path/to/repo --branch dev
    python commit_count_example.py --api-url http://localhost:8080
"""
import argparse
import json
import sys
from os import environ
from pathlib import Path
from typing import Optional

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
    
    def get_commit_count(self, repo_path: Optional[str] = None, branch: Optional[str] = None) -> dict:
        """Get commit count from the API."""
        try:
            # Set repo path if provided
            if repo_path:
                self.set_repo_path(repo_path)
            
            # Build query parameters
            params = {}
            if branch:
                params["branch"] = branch
            
            response = self.session.get(
                f"{self.api_url}/commit_count",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RequestException(f"Failed to get commit count: {e}")


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


def format_output(response: dict, verbose: bool = False) -> str:
    """Format the API response for display."""
    output = []
    
    if response.get("STATUS_CODE") == 200:
        data = response.get("DATA", {})
        commit_count = data.get("commit_count", 0)
        branch_name = data.get("branch", "unknown")
        repo = data.get("repo", "unknown")
        
        # Summary output
        output.append("📊 Commit Count Summary")
        output.append("=" * 50)
        output.append(f"Repository: {repo}")
        output.append(f"Branch: {branch_name or '(current)'}")
        output.append(f"Total commits: {commit_count:,}")
        
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
        description="Get commit count from GitStats API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use default repo and current branch
  %(prog)s --branch main                      # Get count for main branch
  %(prog)s --repo /path/to/repo               # Use specific repository
  %(prog)s --repo /path/to/repo --branch dev  # Use specific repo and branch
  %(prog)s --api-url http://localhost:8080    # Use different API URL
        """
    )
    
    parser.add_argument(
        "--repo", "-r",
        type=str,
        help="Path to the git repository (default: $HOME/repos/gitstats)"
    )
    
    parser.add_argument(
        "--branch", "-b",
        type=str,
        help="Branch name to get commit count for (default: current branch)"
    )
    
    parser.add_argument(
        "--api-url", "-u",
        type=str,
        default="http://127.0.0.1:8000",
        help="GitStats API URL (default: http://127.0.0.1:8000)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show full API response in addition to summary"
    )
    
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Output only raw JSON response"
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
        
        # Create client and get commit count
        client = GitStatsClient(args.api_url)
        
        print(f"🔍 Fetching commit count from {args.api_url}...")
        if args.branch:
            print(f"📋 Branch: {args.branch}")
        if repo_path:
            print(f"📁 Repository: {repo_path}")
        print()
        
        response = client.get_commit_count(repo_path, args.branch)
        
        # Output results
        if args.json_only:
            print(json.dumps(response, indent=2))
        else:
            print(format_output(response, args.verbose))
        
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