#!/usr/bin/env python
# coding: utf-8
"""
Retrieve commit statistics from a Git repository with optional filtering by author, branch, and date range.
"""
import requests
import json
from os import environ
from utils import set_repo_path

def get_commit_statistics(author=None, branch=None, after=None, before=None):
    """
    Fetch commit statistics from a Git repository.

    :param after: Filter commits after a specific or relative date e.g. "1 week ago", "2025-01-01".
    :param author: Filter commits by author e.g. "arobel", "arobel@example.com".
    :param before: Filter commits before a specific or relative date e.g. "today", "yesterday", "2025-07-01".
    :param branch: Specify the branch to analyze e.g. develop, main, feature-branch.
    :return: JSON response with commit statistics.
    """
    url = f"http://localhost:8000/commit_statistics"
    params = {
        "author": author,
        "branch": branch,
        "after": after,
        "before": before
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.json()

if __name__ == "__main__":
    repo_path = f"{environ['HOME']}/repos/wip"
    set_repo_path(repo_path)
    after = "2025-01-01"
    author = "arobel"
    before = "2025-07-01"
    branch = "main"
    try:
        stats = get_commit_statistics(after=after, author=author, before=before, branch=branch)
        print(json.dumps(stats, indent=4))
    except requests.RequestException as error:
        msg = f"Request error occurred.  Check parameters for correctness.\n"
        msg + "Common issues include: \n"
        msg += "  - Incorrect repository path\n"
        msg += "  - Invalid branch name (e.g. does not exist in the repository)\n"
        msg += f"Error detail: {error}"
        print(msg)
