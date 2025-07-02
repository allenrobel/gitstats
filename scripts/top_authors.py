#!/usr/bin/env python
# coding: utf-8
# pylint: disable=line-too-long
"""
Retrieve top authors from a Git repository with optional filtering by branch and date range.
"""
import json
from os import environ

from fastapi import HTTPException
from requests import RequestException

from utils import error_message, get_top_authors, set_repo_path

REPO = f"{environ['HOME']}/repos/gitstats"  # Change to your repository path
AFTER = None  # Set to None to include all commits, or specify a date e.g. "2025-01-01", "1 week ago"
BEFORE = None  # Set to None to include all commits, or specify a date e.g. "2025-07-01", "yesterday"
BRANCH = "main"  # mandatory, specify the branch to analyze e.g. develop, main, feature-branch
LIMIT = 10  # Number of top authors to return (default: 10, max: 100)

set_repo_path(REPO)
try:
    authors = get_top_authors(after=AFTER, before=BEFORE, branch=BRANCH, limit=LIMIT, repo=REPO)
    print(json.dumps(authors, indent=4))
except (HTTPException, RequestException) as error:
    print(error_message(error))
