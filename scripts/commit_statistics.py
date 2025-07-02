#!/usr/bin/env python
# coding: utf-8
"""
Retrieve commit statistics from a Git repository with optional filtering by author, branch, and date range.

This script demonstrates how to use the /commit_statistics endpoint to analyze
repository activity with flexible filtering options for comprehensive code insights.

Usage:
    python commit_stats_example.py [--branch BRANCH] [--author AUTHOR] [--after DATE] [--before DATE] [--repo REPO_PATH]

Examples:
    python commit_stats_example.py --branch main
    python commit_stats_example.py --author "john.doe" --after "2024-01-01"
    python commit_stats_example.py --branch dev --after "1 week ago" --before "today"
    python commit_stats_example.py --author "jane.smith" --branch feature-auth --after "2024-06-01"
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
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
    
    def get_commit_statistics(
        self, 
        repo_path: Optional[str] = None,
        branch: Optional[str] = None,
        author: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None
    ) -> dict:
        """Get commit statistics from the API."""
        try:
            # Set repo path if provided
            if repo_path:
                self.set_repo_path(repo_path)
            
            # Build query parameters
            params = {}
            if branch:
                params["branch"] = branch
            if author:
                params["author"] = author
            if after:
                params["after"] = after
            if before:
                params["before"] = before
            
            response = self.session.get(
                f"{self.api_url}/commit_statistics",
                params=params,
                timeout=60  # Longer timeout for potentially large operations
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RequestException(f"Failed to get commit statistics: {e}")
    
    def get_branches(self, repo_path: Optional[str] = None) -> dict:
        """Get available branches to help with validation."""
        try:
            if repo_path:
                self.set_repo_path(repo_path)
            
            response = self.session.get(f"{self.api_url}/branches", timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RequestException(f"Failed to get branches: {e}")


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


def validate_date_format(date_string: str) -> str:
    """Validate and suggest corrections for date formats."""
    if not date_string:
        return date_string
    
    # Common date formats to try
    formats = [
        "%Y-%m-%d",      # 2024-01-01
        "%m/%d/%Y",      # 01/01/2024
        "%d/%m/%Y",      # 01/01/2024
        "%Y-%m-%d %H:%M:%S",  # 2024-01-01 10:30:00
    ]
    
    # Try to parse as standard date
    for fmt in formats:
        try:
            datetime.strptime(date_string, fmt)
            return date_string  # Valid format
        except ValueError:
            continue
    
    # Check for relative dates (git understands these)
    relative_patterns = [
        "today", "yesterday", "last week", "last month", "last year",
        "1 week ago", "2 weeks ago", "1 month ago", "3 months ago", "1 year ago"
    ]
    
    if any(pattern in date_string.lower() for pattern in relative_patterns):
        return date_string  # Likely valid relative date
    
    # If we get here, suggest common formats
    print(f"⚠️  Warning: Date format '{date_string}' may not be recognized.")
    print("   Suggested formats:")
    print("   - YYYY-MM-DD (e.g., 2024-01-01)")
    print("   - Relative dates (e.g., '1 week ago', 'yesterday', 'last month')")
    print()
    
    return date_string


def format_statistics_summary(data: dict) -> str:
    """Format commit statistics as a comprehensive summary."""
    stats = data.get("commit_statistics", {})
    files = stats.get("files", 0)
    insertions = stats.get("insertions", 0)
    deletions = stats.get("deletions", 0)
    net_lines = insertions - deletions
    
    # Basic info
    repo = data.get("repo", "unknown")
    branch = data.get("branch", "unknown")
    author = stats.get("author")
    after = stats.get("after")
    before = stats.get("before")
    
    output = []
    output.append("📊 Commit Statistics Summary")
    output.append("=" * 60)
    
    # Repository info
    output.append(f"📁 Repository: {repo}")
    output.append(f"🌿 Branch: {branch}")
    
    # Filters applied
    filters = []
    if author:
        filters.append(f"👤 Author: {author}")
    if after:
        filters.append(f"📅 After: {after}")
    if before:
        filters.append(f"📅 Before: {before}")
    
    if filters:
        output.append("")
        output.append("🔍 Filters Applied:")
        for filter_info in filters:
            output.append(f"   {filter_info}")
    
    # Main statistics
    output.append("")
    output.append("📈 Statistics:")
    output.append(f"   📄 Files changed: {files:,}")
    output.append(f"   ➕ Lines added: {insertions:,}")
    output.append(f"   ➖ Lines removed: {deletions:,}")
    output.append(f"   📊 Net change: {net_lines:+,} lines")
    
    # Additional insights
    if files > 0:
        avg_insertions = insertions / files
        avg_deletions = deletions / files
        output.append("")
        output.append("🔢 Averages per file:")
        output.append(f"   ➕ Avg additions: {avg_insertions:.1f} lines")
        output.append(f"   ➖ Avg deletions: {avg_deletions:.1f} lines")
    
    # Activity level indicator
    output.append("")
    if insertions + deletions == 0:
        output.append("💤 Activity level: No changes found")
    elif insertions + deletions < 100:
        output.append("🟢 Activity level: Low (< 100 lines changed)")
    elif insertions + deletions < 1000:
        output.append("🟡 Activity level: Medium (< 1,000 lines changed)")
    elif insertions + deletions < 10000:
        output.append("🟠 Activity level: High (< 10,000 lines changed)")
    else:
        output.append("🔴 Activity level: Very High (10,000+ lines changed)")
    
    return "\n".join(output)


def format_statistics_compact(data: dict) -> str:
    """Format commit statistics in a compact one-line format."""
    stats = data.get("commit_statistics", {})
    files = stats.get("files", 0)
    insertions = stats.get("insertions", 0)
    deletions = stats.get("deletions", 0)
    
    branch = data.get("branch", "unknown")
    author = stats.get("author", "all authors")
    
    return f"📊 {branch} | 👤 {author} | 📄 {files} files | ➕{insertions:,} ➖{deletions:,} lines"


def format_output(response: dict, format_type: str = "summary", verbose: bool = False) -> str:
    """Format the API response for display."""
    output = []
    
    if response.get("STATUS_CODE") == 200:
        data = response.get("DATA", {})
        
        if format_type == "compact":
            output.append(format_statistics_compact(data))
        else:  # summary
            output.append(format_statistics_summary(data))
        
        if verbose:
            output.append("\n" + "=" * 60)
            output.append("📋 Full API Response:")
            output.append(json.dumps(response, indent=2))
    else:
        # Error response
        output.append("❌ Error Response")
        output.append("=" * 50)
        detail = response.get("detail", response)
        if isinstance(detail, dict):
            output.append(json.dumps(detail, indent=2))
        else:
            output.append(str(detail))
    
    return "\n".join(output)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Get commit statistics from GitStats API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --branch main                                    # Stats for main branch
  %(prog)s --author "john.doe"                             # Stats for specific author
  %(prog)s --branch dev --after "2024-01-01"               # Branch stats since Jan 1st
  %(prog)s --author "jane" --after "1 week ago"            # Author stats for last week
  %(prog)s --branch feature --after "2024-06-01" --before "2024-08-01"  # Date range
  %(prog)s --repo /path/to/repo --branch main              # Different repository

Date Examples:
  --after "2024-01-01"        # Specific date
  --after "1 week ago"        # Relative date
  --after "last month"        # Relative date
  --before "yesterday"        # Relative date
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
        help="Branch name to analyze (default: current branch)"
    )
    
    parser.add_argument(
        "--author", "-a",
        type=str,
        help="Filter commits by author (partial name matching)"
    )
    
    parser.add_argument(
        "--after",
        type=str,
        help="Include commits after this date (e.g., '2024-01-01', '1 week ago')"
    )
    
    parser.add_argument(
        "--before",
        type=str,
        help="Include commits before this date (e.g., '2024-12-31', 'yesterday')"
    )
    
    parser.add_argument(
        "--api-url", "-u",
        type=str,
        default="http://127.0.0.1:8000",
        help="GitStats API URL (default: http://127.0.0.1:8000)"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["summary", "compact"],
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
        "--validate-branch",
        action="store_true",
        help="Validate that the specified branch exists before running"
    )
    
    parser.add_argument(
        "--quick-stats",
        action="store_true",
        help="Show only files/insertions/deletions numbers (for scripting)"
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
        
        # Validate date formats
        if args.after:
            args.after = validate_date_format(args.after)
        if args.before:
            args.before = validate_date_format(args.before)
        
        # Create client
        client = GitStatsClient(args.api_url)
        
        # Validate branch if requested
        if args.validate_branch and args.branch:
            print(f"🔍 Validating branch '{args.branch}'...")
            try:
                branches_response = client.get_branches(repo_path)
                if branches_response.get("STATUS_CODE") == 200:
                    available_branches = branches_response.get("DATA", {}).get("branches", [])
                    if args.branch not in available_branches:
                        print(f"❌ Branch '{args.branch}' not found.", file=sys.stderr)
                        print(f"Available branches: {', '.join(available_branches)}", file=sys.stderr)
                        sys.exit(1)
                    print(f"✅ Branch '{args.branch}' found.")
            except RequestException as e:
                print(f"⚠️  Could not validate branch: {e}", file=sys.stderr)
        
        # Show what we're analyzing
        print(f"🔍 Fetching commit statistics from {args.api_url}...")
        if repo_path:
            print(f"📁 Repository: {repo_path}")
        
        filters = []
        if args.branch:
            filters.append(f"Branch: {args.branch}")
        if args.author:
            filters.append(f"Author: {args.author}")
        if args.after:
            filters.append(f"After: {args.after}")
        if args.before:
            filters.append(f"Before: {args.before}")
        
        if filters:
            print(f"🔍 Filters: {' | '.join(filters)}")
        print()
        
        # Get commit statistics
        response = client.get_commit_statistics(
            repo_path=repo_path,
            branch=args.branch,
            author=args.author,
            after=args.after,
            before=args.before
        )
        
        # Output results
        if args.json_only:
            print(json.dumps(response, indent=2))
        elif args.quick_stats and response.get("STATUS_CODE") == 200:
            stats = response.get("DATA", {}).get("commit_statistics", {})
            files = stats.get("files", 0)
            insertions = stats.get("insertions", 0)
            deletions = stats.get("deletions", 0)
            print(f"{files},{insertions},{deletions}")
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
