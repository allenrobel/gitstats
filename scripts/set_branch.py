#!/usr/bin/env python
# coding: utf-8
"""
Set the branch in a Git repository.
"""
import requests
import json
from os import environ
from utils import set_repo_path

def set_branch(branch=None):
    """
    Set the branch in the Git repository.

    :param branch: Specify the branch to set e.g. develop, main, feature-branch.
    :return: JSON response indicating success or failure.
    :raises requests.RequestException: If the request fails.
    """
    url = f"http://localhost:8000/set_branch?branch={branch}"
    response = requests.post(url)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    repo_path = f"{environ['HOME']}/repos/wip"
    set_repo_path(repo_path)
    branch = "main"
    try:
        response = set_branch(branch=branch)
        print(json.dumps(response, indent=4))
    except requests.RequestException as error:
        msg = f"Request error occurred.  Check parameters for correctness.\n"
        msg + "Common issues include: \n"
        msg += "  - Incorrect repository path\n"
        msg += "  - Invalid branch name (e.g. does not exist in the repository)\n"
        msg += f"Error detail: {error}"
        print(msg)
