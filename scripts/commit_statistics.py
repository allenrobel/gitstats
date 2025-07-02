#!/usr/bin/env python
# coding: utf-8
# pylint: disable=line-too-long
"""
Retrieve commit statistics from a Git repository with optional filtering by author, branch, and date range.
"""
import json
from os import environ

from fastapi import HTTPException
from requests import RequestException

from utils import error_message, get_commit_statistics, set_repo_path

REPO = f"{environ['HOME']}/repos/gitstats"
AFTER = None  # Set to None to include all commits, or specify a date e.g. "2025-01-01", "1 week ago"
AUTHOR = None  # Set to None to include all authors, or specify an author e.g. "arobel", "
BEFORE = None  # Set to None to include all commits, or specify a date e.g. "2025-07-01", "yesterday"
BRANCH = "main"  # mandatory, specify the branch to analyze e.g. develop, main, feature-branch
set_repo_path(REPO)
try:
    stats = get_commit_statistics(after=AFTER, author=AUTHOR, before=BEFORE, branch=BRANCH, repo=REPO)
    print(json.dumps(stats, indent=4))
except (HTTPException, RequestException) as error:
    print(error_message(error))
