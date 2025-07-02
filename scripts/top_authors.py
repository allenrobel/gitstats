#!/usr/bin/env python
# coding: utf-8
"""
Retrieve top authors from a Git repository with optional filtering by branch and date range.

This script demonstrates how to use the /top_authors endpoint to analyze
contributor activity and identify the most active developers in your repository.

Usage:
    python top_authors_example.py [--branch BRANCH] [--limit N] [--after DATE] [--before DATE] [--repo REPO_PATH]

Examples:
    python top_authors_example.py --branch main --limit 5
    python top_authors_example.py --after "2024-01-01" --limit 20
    python top_authors_example.py --branch dev --after "1 month ago" --before "today"
    python top_authors_example.py --limit 3 --format leaderboard
"""
import argparse
import json
import sys
from datetime import datetime
from os import environ
from pathlib import Path
from typing import Optional, List, Dict

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
    
    def get_top_authors(
        self, 
        repo_path: Optional[str] = None,
        branch: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        limit: int = 10
    ) -> dict:
        """Get top authors from the API."""
        try:
            # Set repo path if provided
            if repo_path:
                self.set_repo_path(repo_path)
            
            # Build query parameters
            params = {"limit": limit}
            if branch:
                params["branch"] = branch
            if after:
                params["after"] = after
            if before:
                params["before"] = before
            
            response = self.session.get(
                f"{self.api_url}/top_authors",
                params=params,
                timeout=60  # Longer timeout for potentially large operations
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RequestException(f"Failed to get top authors: {e}")
    
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


def get_medal_emoji(rank: int) -> str:
    """Get appropriate medal emoji for ranking."""
    if rank == 1:
        return "🥇"
    elif rank == 2:
        return "🥈"
    elif rank == 3:
        return "🥉"
    else:
        return f"{rank:2d}."


def format_leaderboard(authors: List[Dict], total_authors: int, filters: Dict) -> str:
    """Format authors as a leaderboard with rankings and visual elements."""
    if not authors:
        return "No authors found matching the criteria."
    
    output = []
    output.append("🏆 Developer Leaderboard")
    output.append("=" * 70)
    
    # Show filters if any
    filter_info = []
    if filters.get("branch"):
        filter_info.append(f"🌿 Branch: {filters['branch']}")
    if filters.get("after"):
        filter_info.append(f"📅 After: {filters['after']}")
    if filters.get("before"):
        filter_info.append(f"📅 Before: {filters['before']}")
    
    if filter_info:
        output.append(" | ".join(filter_info))
        output.append("-" * 70)
    
    # Calculate max name width for alignment
    max_name_width = max(len(author["name"]) for author in authors) if authors else 10
    max_name_width = max(max_name_width, 15)  # Minimum width
    
    # Header
    output.append(f"{'Rank':<6} {'Developer':<{max_name_width}} {'Commits':<10} {'Activity'}")
    output.append("-" * (6 + max_name_width + 20))
    
    # Find max commits for progress bar scaling
    max_commits = max(author["commit_count"] for author in authors) if authors else 1
    
    # Author rankings
    for i, author in enumerate(authors, 1):
        name = author["name"]
        commits = author["commit_count"]
        medal = get_medal_emoji(i)
        
        # Create a visual progress bar
        bar_length = 20
        filled_length = int((commits / max_commits) * bar_length) if max_commits > 0 else 0
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        output.append(f"{medal:<6} {name:<{max_name_width}} {commits:<10,} {bar}")
    
    output.append("")
    output.append(f"📊 Showing top {len(authors)} of {total_authors} total contributors")
    
    # Calculate some basic stats
    if authors:
        total_commits = sum(author["commit_count"] for author in authors)
        avg_commits = total_commits / len(authors)
        top_author = authors[0]
        
        output.append("")
        output.append("📈 Statistics:")
        output.append(f"   🎯 Top contributor: {top_author['name']} ({top_author['commit_count']:,} commits)")
        output.append(f"   📊 Total commits (top {len(authors)}): {total_commits:,}")
        output.append(f"   📊 Average commits: {avg_commits:.1f}")
        
        if len(authors) > 1:
            commit_range = authors[0]["commit_count"] - authors[-1]["commit_count"]
            output.append(f"   📏 Commit range: {commit_range:,} commits")
    
    return "\n".join(output)


def format_table(authors: List[Dict], total_authors: int, filters: Dict) -> str:
    """Format authors as a clean table."""
    if not authors:
        return "No authors found matching the criteria."
    
    output = []
    output.append("👥 Top Contributors")
    output.append("=" * 50)
    
    # Calculate max name width for alignment
    max_name_width = max(len(author["name"]) for author in authors) if authors else 10
    max_name_width = max(max_name_width, 15)
    
    # Header
    output.append(f"{'#':<4} {'Author':<{max_name_width}} {'Commits':<10} {'%'}")
    output.append("-" * (4 + max_name_width + 20))
    
    # Calculate total commits for percentage
    total_commits = sum(author["commit_count"] for author in authors) if authors else 1
    
    # Author list
    for i, author in enumerate(authors, 1):
        name = author["name"]
        commits = author["commit_count"]
        percentage = (commits / total_commits * 100) if total_commits > 0 else 0
        
        output.append(f"{i:<4} {name:<{max_name_width}} {commits:<10,} {percentage:5.1f}%")
    
    output.append("")
    output.append(f"Total: {len(authors)} of {total_authors} contributors shown")
    
    return "\n".join(output)


def format_compact(authors: List[Dict], total_authors: int, filters: Dict) -> str:
    """Format authors in a compact single-line format."""
    if not authors:
        return "No authors found."
    
    author_list = []
    for i, author in enumerate(authors[:5], 1):  # Show top 5 in compact mode
        author_list.append(f"{i}.{author['name']}({author['commit_count']})")
    
    result = " | ".join(author_list)
    if len(authors) > 5:
        result += f" | +{len(authors)-5} more"
    
    return f"👥 Top Authors: {result}"


def format_names_only(authors: List[Dict]) -> str:
    """Format just the author names for scripting."""
    return "\n".join(author["name"] for author in authors)


def format_output(response: dict, format_type: str = "leaderboard", verbose: bool = False) -> str:
    """Format the API response for display."""
    output = []
    
    if response.get("STATUS_CODE") == 200:
        data = response.get("DATA", {})
        authors = data.get("top_authors", [])
        total_authors = data.get("total_authors", 0)
        
        # Extract filter information
        filters = {
            "branch": data.get("branch"),
            "after": data.get("after"),
            "before": data.get("before"),
            "repo": data.get("repo")
        }
        
        if format_type == "table":
            output.append(f"📁 Repository: {filters.get('repo', 'unknown')}")
            output.append("")
            output.append(format_table(authors, total_authors, filters))
        elif format_type == "compact":
            output.append(format_compact(authors, total_authors, filters))
        elif format_type == "names":
            output.append(format_names_only(authors))
        else:  # leaderboard
            output.append(f"📁 Repository: {filters.get('repo', 'unknown')}")
            output.append("")
            output.append(format_leaderboard(authors, total_authors, filters))
        
        if verbose and format_type != "names":
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
        description="Get top authors from GitStats API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --branch main --limit 5                         # Top 5 authors on main
  %(prog)s --after "2024-01-01" --limit 20                 # Top 20 authors since Jan 1st
  %(prog)s --branch dev --after "1 month ago"              # Recent activity on dev branch
  %(prog)s --limit 3 --format leaderboard                  # Top 3 with visual leaderboard
  %(prog)s --before "2024-06-30" --format table            # Contributors before June 30th
  %(prog)s --format names --limit 10                       # Just names for scripting

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
        "--limit", "-l",
        type=int,
        default=10,
        help="Number of top authors to return (default: 10, max: 100)"
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
        choices=["leaderboard", "table", "compact", "names"],
        default="leaderboard",
        help="Output format (default: leaderboard)"
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
        "--top-only",
        type=int,
        metavar="N",
        help="Show only the top N author(s) with detailed info"
    )
    
    parser.add_argument(
        "--min-commits",
        type=int,
        default=1,
        help="Only show authors with at least N commits (default: 1)"
    )
    
    return parser.parse_args()


def main():
    """Main function."""
    try:
        args = parse_arguments()
        
        # Validate limit
        if args.limit < 1 or args.limit > 100:
            print("❌ Error: Limit must be between 1 and 100", file=sys.stderr)
            sys.exit(1)
        
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
        print(f"🔍 Fetching top authors from {args.api_url}...")
        if repo_path:
            print(f"📁 Repository: {repo_path}")
        
        filters = []
        if args.branch:
            filters.append(f"Branch: {args.branch}")
        if args.after:
            filters.append(f"After: {args.after}")
        if args.before:
            filters.append(f"Before: {args.before}")
        filters.append(f"Limit: {args.limit}")
        
        if filters:
            print(f"🔍 Filters: {' | '.join(filters)}")
        print()
        
        # Get top authors
        response = client.get_top_authors(
            repo_path=repo_path,
            branch=args.branch,
            after=args.after,
            before=args.before,
            limit=args.limit
        )
        
        # Apply additional filtering if requested
        if response.get("STATUS_CODE") == 200 and (args.min_commits > 1 or args.top_only):
            data = response.get("DATA", {})
            authors = data.get("top_authors", [])
            
            # Filter by minimum commits
            if args.min_commits > 1:
                authors = [a for a in authors if a["commit_count"] >= args.min_commits]
            
            # Limit to top N with detailed info
            if args.top_only:
                authors = authors[:args.top_only]
            
            # Update the response
            response["DATA"]["top_authors"] = authors
        
        # Output results
        if args.json_only:
            print(json.dumps(response, indent=2))
        elif args.top_only and response.get("STATUS_CODE") == 200:
            # Special detailed view for top-only mode
            data = response.get("DATA", {})
            authors = data.get("top_authors", [])
            if authors:
                print(f"🏆 Top {len(authors)} Contributor{'s' if len(authors) != 1 else ''}:")
                print("=" * 50)
                for i, author in enumerate(authors, 1):
                    medal = get_medal_emoji(i)
                    print(f"{medal} {author['name']}: {author['commit_count']:,} commits")
            else:
                print("No authors found matching the criteria.")
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
