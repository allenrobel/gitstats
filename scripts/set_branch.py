#!/usr/bin/env python
# coding: utf-8
# pylint: disable=line-too-long
"""
Set the branch in a Git repository.
"""
import json
from os import environ

from requests import RequestException

from utils import error_message, set_branch, set_repo_path

repo_path = f"{environ['HOME']}/repos/wip"
set_repo_path(repo_path)
BRANCH = "main"
try:
    response = set_branch(branch=BRANCH)
    print(json.dumps(response, indent=4))
except RequestException as error:
    print(error_message(error))
