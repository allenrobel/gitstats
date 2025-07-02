# coding: utf-8
# pylint: disable=line-too-long
"""
Utility functions for interacting with FastAPI application gitstats repository.
"""
import requests


def set_repo_path(repo):
    """
    Set the path to the Git repository.

    :param repo: Absolute path to the Git repository.
    """
    url = f"http://localhost:8000/set_repo?repo={repo}"
    requests.post(url, timeout=10)


def get_branches(repo=None):
    """
    Fetch a list of local branches from a Git repository.

    :return: JSON response with a list of local branches.
    """
    if repo:
        set_repo_path(repo)

    msg = f"get_branches: using repo {repo}"
    print(msg)
    url = "http://localhost:8000/branches"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def get_commit_statistics(author=None, branch=None, after=None, before=None, repo=None):
    """
    Fetch commit statistics from a Git repository.

    :param after: Filter commits after a specific or relative date e.g. "1 week ago", "2025-01-01".
    :param author: Filter commits by author e.g. "arobel", "arobel@example.com".
    :param before: Filter commits before a specific or relative date e.g. "today", "yesterday", "2025-07-01".
    :param branch: Specify the branch to analyze e.g. develop, main, feature-branch.
    :return: JSON response with commit statistics.
    """
    url = "http://localhost:8000/commit_statistics"
    params = {"author": author, "branch": branch, "after": after, "before": before, "repo": repo}
    # print(f"params: {params}")

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    return response.json()


def error_message(error):
    """
    Format an error message for request exceptions.

    :param error: The exception raised during the request.
    :return: Formatted error message.
    """
    msg = "Request error occurred. Check parameters for correctness.\n"
    msg += "Common issues include:\n"
    msg += "  - Incorrect repository path\n"
    msg += "  - Invalid branch name (e.g. does not exist in the repository)\n"
    msg += f"Error detail: {error}"
    return msg


def set_branch(branch=None):
    """
    Set the branch in the Git repository.

    :param branch: Specify the branch to set e.g. develop, main, feature-branch.
    :return: JSON response indicating success or failure.
    :raises requests.RequestException: If the request fails.
    """
    url = f"http://localhost:8000/set_branch?branch={branch}"
    response = requests.post(url, timeout=10)
    response.raise_for_status()
    return response.json()
