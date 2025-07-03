#!/usr/bin/env python
# coding: utf-8
"""
Set the active branch for GitStats API operations in a Git repository.

This script demonstrates how to use the /set_branch endpoint to configure
which branch will be used for subsequent API operations, with intelligent
branch validation and interactive selection capabilities.

Usage:
    python set_branch_example.py [--branch BRANCH] [--repo REPO_PATH] [--interactive]

Examples:
    python set_branch_example.py --branch main
    python set_branch_example.py --branch dev --repo /path/to/repo
    python set_branch_example.py --interactive
    python set_branch_example.py --list-branches
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
    
    def set_branch(self, branch: Optional[str] = None) -> dict:
        """Set the active branch in the API."""
        try:
            params = {}
            if branch:
                params["branch"] = branch
            
            response = self.session.post(
                f"{self.api_url}/set_branch",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RequestException(f"Failed to set branch: {e}")
    
    def get_branches(self) -> dict:
        """Get available branches from the API."""
        try:
            response = self.session.get(f"{self.api_url}/branches", timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RequestException(f"Failed to get branches: {e}")
    
    def get_current_branch(self) -> dict:
        """Get current branch from the API."""
        try:
            response = self.session.get(f"{self.api_url}/current_branch", timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RequestException(f"Failed to get current branch: {e}")
    
    def get_current_branch_internal(self) -> dict:
        """Get internally set branch from the API."""
        try:
            response = self.session.get(f"{self.api_url}/current_branch_internal", timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RequestException(f"Failed to get internal branch: {e}")


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


def interactive_branch_selection(branches: List[str], current_branch: str) -> Optional[str]:
    """Interactive branch selection with numbered menu."""
    if not branches:
        print("❌ No branches available for selection.")
        return None
    
    print("\n🌿 Available Branches:")
    print("=" * 40)
    
    # Sort branches with current branch first
    sorted_branches = sorted(branches)
    if current_branch and current_branch in sorted_branches:
        sorted_branches.remove(current_branch)
        sorted_branches.insert(0, current_branch)
    
    for i, branch in enumerate(sorted_branches, 1):
        marker = "📍 (current)" if branch == current_branch else ""
        print(f"{i:2d}. {branch} {marker}")
    
    print(f"\n{len(sorted_branches)+1:2d}. Clear branch setting (use repo default)")
    print(f"{len(sorted_branches)+2:2d}. Cancel")
    
    while True:
        try:
            choice = input(f"\nSelect branch (1-{len(sorted_branches)+2}): ").strip()
            
            if not choice:
                continue
            
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(sorted_branches):
                selected_branch = sorted_branches[choice_num - 1]
                print(f"✅ Selected: {selected_branch}")
                return selected_branch
            elif choice_num == len(sorted_branches) + 1:
                print("✅ Branch setting will be cleared")
                return ""  # Empty string to clear branch
            elif choice_num == len(sorted_branches) + 2:
                print("❌ Operation cancelled")
                return None
            else:
                print(f"❌ Invalid choice. Please enter 1-{len(sorted_branches)+2}")
        
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled")
            return None


def format_branch_status(response: dict) -> str:
    """Format the branch setting response with status information."""
    if response.get("STATUS_CODE") != 200:
        return "❌ Failed to set branch"
    
    data = response.get("DATA", {})
    branch = data.get("branch")
    repo = data.get("repo", "unknown")
    
    output = []
    output.append("✅ Branch Configuration Updated")
    output.append("=" * 50)
    output.append(f"📁 Repository: {repo}")
    
    if branch:
        output.append(f"🌿 Active branch: {branch}")
        output.append("\n💡 This branch will be used for subsequent API operations")
        output.append("   (unless overridden by specific endpoint parameters)")
    else:
        output.append("🌿 Active branch: (cleared - will use repository default)")
        output.append("\n💡 API operations will use the repository's current branch")
    
    return "\n".join(output)


def format_branch_comparison(before_response: dict, after_response: dict) -> str:
    """Format a before/after comparison of branch settings."""
    before_data = before_response.get("DATA", {}) if before_response.get("STATUS_CODE") == 200 else {}
    after_data = after_response.get("DATA", {}) if after_response.get("STATUS_CODE") == 200 else {}
    
    before_branch = before_data.get("branch") or "(repository default)"
    after_branch = after_data.get("branch") or "(repository default)"
    
    output = []
    output.append("🔄 Branch Setting Change")
    output.append("=" * 40)
    output.append(f"Before: {before_branch}")
    output.append(f"After:  {after_branch}")
    
    if before_branch != after_branch:
        output.append("\n✅ Branch setting successfully updated!")
    else:
        output.append("\n💡 Branch setting unchanged")
    
    return "\n".join(output)


def list_branches_with_status(client: GitStatsClient) -> str:
    """List all branches with current status indicators."""
    try:
        # Get all information
        branches_response = client.get_branches()
        current_response = client.get_current_branch()
        internal_response = client.get_current_branch_internal()
        
        if branches_response.get("STATUS_CODE") != 200:
            return "❌ Failed to get branch information"
        
        branches_data = branches_response.get("DATA", {})
        current_data = current_response.get("DATA", {}) if current_response.get("STATUS_CODE") == 200 else {}
        internal_data = internal_response.get("DATA", {}) if internal_response.get("STATUS_CODE") == 200 else {}
        
        branches = branches_data.get("branches", [])
        repo_current = current_data.get("branch", "")
        api_current = internal_data.get("branch", "")
        repo = branches_data.get("repo", "unknown")
        
        output = []
        output.append("🌿 Branch Status Overview")
        output.append("=" * 60)
        output.append(f"📁 Repository: {repo}")
        output.append(f"🏠 Repository current: {repo_current or '(unknown)'}")
        output.append(f"⚙️  API setting: {api_current or '(not set - using repo default)'}")
        output.append("")
        
        if not branches:
            output.append("No branches found.")
            return "\n".join(output)
        
        output.append("Available branches:")
        output.append("-" * 30)
        
        # Sort branches
        sorted_branches = sorted(branches)
        
        for branch in sorted_branches:
            indicators = []
            if branch == repo_current:
                indicators.append("🏠 repo")
            if branch == api_current:
                indicators.append("⚙️ api")
            
            status = f" ({', '.join(indicators)})" if indicators else ""
            output.append(f"  🌿 {branch}{status}")
        
        output.append("")
        output.append(f"Total: {len(branches)} branches")
        
        return "\n".join(output)
        
    except RequestException as e:
        return f"❌ Error getting branch information: {e}"


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Set active branch for GitStats API operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --branch main                    # Set API to use main branch
  %(prog)s --branch dev --repo /path/repo   # Set branch for specific repo
  %(prog)s --clear                          # Clear branch setting (use repo default)
  %(prog)s --interactive                    # Interactive branch selection
  %(prog)s --list-branches                  # Show all branches with status
  %(prog)s --status                         # Show current branch configuration

Notes:
  - Setting a branch affects ALL subsequent API operations
  - Individual endpoints can still override with their own branch parameter
  - Use --clear to reset to repository default behavior
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
        help="Branch name to set as active"
    )
    
    parser.add_argument(
        "--api-url", "-u",
        type=str,
        default="http://127.0.0.1:8000",
        help="GitStats API URL (default: http://127.0.0.1:8000)"
    )
    
    parser.add_argument(
        "--clear", "-c",
        action="store_true",
        help="Clear the branch setting (use repository default)"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Interactive branch selection from available branches"
    )
    
    parser.add_argument(
        "--list-branches", "-l",
        action="store_true",
        help="List all branches with current status"
    )
    
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show current branch configuration"
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
        "--compare",
        action="store_true",
        help="Show before/after comparison when setting branch"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate that the branch exists before setting it"
    )
    
    return parser.parse_args()


def main():
    """Main function."""
    try:
        args = parse_arguments()
        
        # Validate arguments
        action_count = sum([
            bool(args.branch),
            args.clear,
            args.interactive,
            args.list_branches,
            args.status
        ])
        
        if action_count == 0:
            print("❌ Error: Must specify an action (--branch, --clear, --interactive, --list-branches, or --status)")
            print("Use --help for usage information.")
            sys.exit(1)
        
        if action_count > 1:
            print("❌ Error: Only one action can be specified at a time")
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
        
        # Create client
        client = GitStatsClient(args.api_url)
        
        # Set repository path
        print(f"🔍 Connecting to GitStats API at {args.api_url}...")
        if repo_path:
            print(f"📁 Repository: {repo_path}")
            client.set_repo_path(repo_path)
        print()
        
        # Handle different actions
        if args.list_branches:
            # List branches with status
            result = list_branches_with_status(client)
            print(result)
            
        elif args.status:
            # Show current status
            try:
                current_response = client.get_current_branch()
                internal_response = client.get_current_branch_internal()
                
                if args.json_only:
                    status_data = {
                        "current_branch": current_response,
                        "internal_branch": internal_response
                    }
                    print(json.dumps(status_data, indent=2))
                else:
                    current_data = current_response.get("DATA", {}) if current_response.get("STATUS_CODE") == 200 else {}
                    internal_data = internal_response.get("DATA", {}) if internal_response.get("STATUS_CODE") == 200 else {}
                    
                    repo_current = current_data.get("branch", "(unknown)")
                    api_current = internal_data.get("branch") or "(not set)"
                    repo = current_data.get("repo", "unknown")
                    
                    print("📊 Current Branch Configuration")
                    print("=" * 50)
                    print(f"📁 Repository: {repo}")
                    print(f"🏠 Repository current branch: {repo_current}")
                    print(f"⚙️  API active branch: {api_current}")
                    
                    if api_current == "(not set)":
                        print("\n💡 API will use the repository's current branch for operations")
                    else:
                        print(f"\n💡 API will use '{internal_data.get('branch')}' for operations")
                        print("   (unless overridden by endpoint parameters)")
            
            except RequestException as e:
                print(f"❌ Error getting status: {e}", file=sys.stderr)
                sys.exit(1)
        
        else:
            # Handle branch setting operations
            before_response = None
            if args.compare:
                try:
                    before_response = client.get_current_branch_internal()
                except RequestException:
                    pass  # Continue without comparison
            
            # Determine target branch
            target_branch = None
            
            if args.clear:
                target_branch = ""  # Empty string clears the setting
                print("🗑️  Clearing branch setting...")
                
            elif args.branch:
                target_branch = args.branch
                
                # Validate branch if requested
                if args.validate:
                    print(f"🔍 Validating branch '{target_branch}'...")
                    try:
                        branches_response = client.get_branches()
                        if branches_response.get("STATUS_CODE") == 200:
                            available_branches = branches_response.get("DATA", {}).get("branches", [])
                            if target_branch not in available_branches:
                                print(f"❌ Branch '{target_branch}' not found.", file=sys.stderr)
                                print(f"Available branches: {', '.join(available_branches)}", file=sys.stderr)
                                sys.exit(1)
                            print(f"✅ Branch '{target_branch}' found.")
                        else:
                            print("⚠️  Could not validate branch (continuing anyway)")
                    except RequestException as e:
                        print(f"⚠️  Could not validate branch: {e}")
                
                print(f"🌿 Setting active branch to '{target_branch}'...")
                
            elif args.interactive:
                # Interactive selection
                try:
                    branches_response = client.get_branches()
                    current_response = client.get_current_branch_internal()
                    
                    if branches_response.get("STATUS_CODE") != 200:
                        print("❌ Failed to get available branches for selection", file=sys.stderr)
                        sys.exit(1)
                    
                    branches = branches_response.get("DATA", {}).get("branches", [])
                    current_internal = ""
                    if current_response.get("STATUS_CODE") == 200:
                        current_internal = current_response.get("DATA", {}).get("branch", "")
                    
                    target_branch = interactive_branch_selection(branches, current_internal)
                    if target_branch is None:
                        print("Operation cancelled.")
                        sys.exit(0)
                
                except RequestException as e:
                    print(f"❌ Error during interactive selection: {e}", file=sys.stderr)
                    sys.exit(1)
            
            # Set the branch
            try:
                if target_branch == "":
                    response = client.set_branch(None)  # Clear setting
                else:
                    response = client.set_branch(target_branch)
                
                # Output results
                if args.json_only:
                    print(json.dumps(response, indent=2))
                elif args.compare and before_response:
                    print(format_branch_comparison(before_response, response))
                    if args.verbose:
                        print("\n" + "=" * 50)
                        print("📋 Full API Response:")
                        print(json.dumps(response, indent=2))
                else:
                    print(format_branch_status(response))
                    if args.verbose:
                        print("\n" + "=" * 50)
                        print("📋 Full API Response:")
                        print(json.dumps(response, indent=2))
                
                # Exit with appropriate code
                sys.exit(0 if response.get("STATUS_CODE") == 200 else 1)
                
            except RequestException as e:
                print(f"❌ Error setting branch: {e}", file=sys.stderr)
                sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()