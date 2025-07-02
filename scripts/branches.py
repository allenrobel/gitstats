#!/usr/bin/env python
# coding: utf-8
# pylint: disable=line-too-long
"""
Retrieve a list of local branches from a Git repository.

Edit the following line to set the path to your Git repository:

repo_path = f"{environ['HOME']}/repos/gitstats"
"""
import json
from os import environ

from requests import RequestException

from utils import error_message, get_branches, set_repo_path

repo_path = f"{environ['HOME']}/repos/gitstats"
set_repo_path(repo_path)
try:
    response = get_branches(repo_path)
    print(json.dumps(response, indent=4))
except RequestException as error:
    print(error_message(error))
