#!/usr/bin/env python
"""
# Summary

A FastAPI application for retrieving statistics from a Git repository.
"""
import logging
import os
import re
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Union

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field


def get_logger():
    """Initialize and return a logger."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)  # Set the minimum logging level
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


def get_repo_path(repo: str = None) -> Path:
    """
    # Summary

    Return a Path object representing the repository path.

    # Parameters

    - repo (str): Optional.
      - If set to ENV, the value of the environment variable GITSTATS_REPO_PATH is used.
      - If set to a string, an absolute path to a repository is assumed and used.

    # Raises

    - HTTPException: If the repository path cannot be determined or is not a valid directory.

    # Returns

    A Path object representing the repository path.
    """
    repo_path = None
    if not repo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing repo parameter.")
    if repo == "ENV":
        repo_path = os.environ.get("GITSTATS_REPO_PATH", None)
        if not repo_path:
            return None
    repo_path = repo
    # Ensure the repo path is absolute
    repo_path = Path(os.path.expanduser(repo_path)).resolve()
    if not repo_path.is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Repository path {repo_path} does not exist or is not a directory.")
    return repo_path


def set_app_commands(instance: FastAPI) -> None:
    """
    Set the git command templates for the app.
    """
    instance.repo_command = ["git", "-C", f"{instance.repo_path}"]
    instance.log_command = instance.repo_command + ["log"]
    instance.log_stat_command = instance.log_command + ["--stat"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    # Summary

    Initialize the application.

    1. Set up the logger.
    2. Try to set the repository path from the environment variable `GITSTATS_REPO_PATH`.
    3. Initialize the branch to None.
    4. If the repository path is set, configure the app command templates used by the application.
    """
    app.log = get_logger()
    app.log.debug("Initializing GitStats API application...")
    app.repo_path = get_repo_path("ENV")  # Default to the environment variable GITSTATS_REPO_PATH
    app.branch = None
    msg = f"Repository path: {app.repo_path}"
    app.log.debug(msg)
    if app.repo_path:
        set_app_commands(app)
    yield


app = FastAPI(title="GitStats API", description="A FastAPI application for retrieving statistics from a Git repository.", version="1.0.0", lifespan=lifespan)


def response_400(response: dict):
    """
    # Summary

    IF `response` contains an "ERROR" key, raise an HTTPException with a 400 status code.

    The error response will have the following structure (assuming the caller
    has populated `response` with ERROR, REQUEST_PATH, and REQUEST_METHOD).

    {
        "detail": {
            "ERROR": "The error message",
            "REQUEST_PATH": "/commit_statistics",
            "REQUEST_METHOD": "GET",
            "STATUS_CODE": 400
        }
    }
    """
    if response.get("ERROR"):
        if not response.get("REQUEST_PATH"):
            response["REQUEST_PATH"] = "/unknown"
        if not response.get("REQUEST_METHOD"):
            response["REQUEST_METHOD"] = "UNKNOWN"
        response["STATUS_CODE"] = status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=response)


def response_200(response: dict):
    """
    # Summary

    Create a success response with the following structure.

    {
        "DATA": {
            <your data as a dictionary>
        },
        "status_code": 200
    }
    """
    response.pop("command_output", None)
    response.update({"STATUS_CODE": status.HTTP_200_OK})
    return response


def error_no_repo():
    """
    # Summary

    Raise an HTTP 400 error if the repository path is not set.

    # Raises

    HTTPException: If the repository path is not set.
    """
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repository path is not set. Use /set_repo to set the repository path.")


def branches_in_repo(app) -> list:
    """
    # Summary

    Get the list of branches in the repository.

    # Returns

    A list of branch names.
    """
    command = app.repo_command + ["branch", "--list"]
    output = exec_command(command)
    if "ERROR" in output:
        return []
    command_output = output.get("command_output", "")
    branches = [line.strip() for line in command_output.splitlines() if line.strip()]
    # Remove leading '*' from the current branch
    branches = [line.lstrip("*").strip() for line in branches]
    return branches


def is_branch_in_repo(app, branch: str) -> bool:
    """
    # Summary

    Check if a branch exists in the repository.

    # Returns

    True if the branch exists, False otherwise.
    """
    branches = branches_in_repo(app)
    return branch in branches


def current_branch_in_repo(app) -> str:
    """
    # Summary

    Get the current branch in the repository.

    # Returns

    The name of the current branch as a string.
    """
    if app.branch:
        app.log.debug(f"Using previously-set branch: {app.branch}")
        return app.branch
    command = app.repo_command + ["branch", "--show-current"]
    output = exec_command(command)
    if "ERROR" in output:
        return ""
    return output.get("command_output", "").strip()


def exec_command(command: list):
    """
    # Summary

    Execute a shell command and return the output.

    # Parameters

    - command (list): A list of strings representing the command and its arguments.

    # Returns

    Either a dictionary with the command output or an error message if the command fails.

    ## Success Response

    ```json
    {
        "command_output": "output of the command"
    }
    ```

    ## Error Response

    ```json
    {
        "ERROR": "error message from the command"
    }
    ```
    """
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return {"command_output": result.stdout.strip()}
    except subprocess.CalledProcessError as e:
        return {"ERROR": e.stderr.strip()}


class CommitCountParams(BaseModel):
    branch: Union[str | None] = Field(
        default=None,
        title="Branch Name",
        description="The name of the branch to query. This overrides the current branch set with `/set_branch`.",
        deprecated=False,
    )


@app.get("/commit_count", tags=["Repository Statistics"])
async def get_commit_count(params: Annotated[CommitCountParams, Query()] = None):
    """
    # Summary

    Get the total number of commits in the repository.

    ## Git Command

    ```bash
    git -C <repo_path> rev-list --count HEAD
    ```

    ## Parameters

    - `branch`: (optional) The name of the branch for which the commit count is requested.
      This overrides the current branch set with `/set_branch`.

    ## Example usage

    ### Example without branch

    - If the `branch` parameter is not provided, the commit count for the current branch is returned.
    - See also: `/set_branch` to set the current branch.

    #### Command

    ```command
    curl 'http://localhost:8000/commit_count'
    ```

    #### JSON Response

    ```json response
    {
        "REQUEST_PATH": "/commit_count",
        "REQUEST_METHOD": "GET",
        "DATA": {
            "commit_count": 123,
            "branch": "main",
            "repo": "/path/to/repo"
        },
        "STATUS_CODE": 200
    }
    ```

    ### Example with branch

    - If the `branch` parameter is provided, the commit count for that branch is returned.
    - If the branch does not exist, a 400 error is returned.

    #### Command

    ```command
    curl 'http://localhost:8000/commit_count?branch=dev'
    ```

    #### JSON Response

    ```json response
    {
        "REQUEST_PATH": "/commit_count",
        "REQUEST_METHOD": "GET",
        "DATA": {
            "commit_count": 45,
            "branch": "dev",
            "repo": "/path/to/repo"
        },
        "STATUS_CODE": 200
    }
    ```

    """
    if not app.repo_path:
        error_no_repo()
    response = {}
    response.update({"REQUEST_PATH": "/commit_count"})
    response.update({"REQUEST_METHOD": "GET"})
    command = app.repo_command + ["rev-list", "--count", "HEAD"]  # pylint: disable=no-member
    branch = None
    if params.branch:
        if not is_branch_in_repo(app, params.branch):
            error = f"Branch '{params.branch}' does not exist in the repository {app.repo_path}"
            response.update({"ERROR": error})
            response_400(response)
        msg = f"Using branch: {params.branch}"
        app.log.debug(msg)
        command.append(params.branch)
        branch = params.branch
    elif app.branch:
        msg = f"Using previously-set branch: {app.branch}"
        app.log.debug(msg)
        command.append(app.branch)
        branch = app.branch
    msg = f"command: {' '.join(command)}"
    app.log.debug(msg)
    output = exec_command(command)
    response.update({"command_output": output.get("command_output", "")})
    response_400(response)
    response.update({"DATA": {"commit_count": int(output.get("command_output")), "branch": branch, "repo": str(app.repo_path)}})
    return response_200(response)


@app.get("/branches", tags=["Branch Management"])
async def get_branches():
    """
    # Summary

    Get the list of branches in the local repository.

    ## Git Command

    ```bash
    git -C <repo_path> branch --list
    ```

    ## Example usage

    ### Command

    ```command
    curl 'http://127.0.0.1:8000/branches'
    ```

    ### JSON Response

    - `DATA.branches`: List of branches in the repository.
    - `DATA.branch`: The current branch in the repository.
    - `DATA.repo`: The path to the repository.

    ```json response
    {
        "REQUEST_PATH": "/branches",
        "REQUEST_METHOD": "GET",
        "DATA": {
            "branches": ["dev", "main"],
            "branch": "dev",
            "repo": "/path/to/repo"
        },
        "STATUS_CODE": 200
    }
    ```
    """
    if not app.repo_path:
        error_no_repo()
    response = {}
    response.update({"REQUEST_PATH": "/branches"})
    response.update({"REQUEST_METHOD": "GET"})
    command = app.repo_command + ["branch", "--list"]  # pylint: disable=no-member

    msg = f"command: {' '.join(command)}"
    app.log.debug(msg)

    output = exec_command(command)
    command_output = output.get("command_output", "")
    response.update({"command_output": command_output})
    response_400(response)
    branches = [line.strip() for line in command_output.splitlines() if line.strip()]
    # Remove leading '*' from the current branch
    branches = [line.lstrip("*").strip() for line in branches]
    data = {"branches": branches, "branch": current_branch_in_repo(app), "repo": str(app.repo_path)}
    response.update({"DATA": data})
    return response_200(response)


@app.get("/current_branch", tags=["Branch Management"])
async def get_current_branch():
    """
    # Summary

    Return the branch that the repository is currently set to.

    ## Git Command

    ```bash
    git -C <repo_path> branch --show-current
    ```

    ## Example usage

    ### Command

    ```command
    curl 'http://127.0.0.1:8000/current_branch'
    ```

    ### JSON Response

    - `DATA.branch`: The current branch in the repository.
    - `DATA.repo`: The path to the repository.

    ```json response
    {
        "REQUEST_PATH": "/current_branch",
        "REQUEST_METHOD": "GET",
        "DATA": {
            "branch": "dcnm-vrf-pydantic-integration",
            "repo": "/path/to/repo"
        },
        "STATUS_CODE": 200
    }
    ```
    """
    if not app.repo_path:
        error_no_repo()
    response = {}
    response.update({"REQUEST_PATH": "/current_branch"})
    response.update({"REQUEST_METHOD": "GET"})
    if app.branch:
        msg = f"Using previously-set branch: {app.branch}"
        app.log.debug(msg)
        data = {}
        data["branch"] = app.branch
        data["repo"] = str(app.repo_path)
        response.update({"DATA": data})
        return response_200(response)
    command = app.repo_command + ["branch", "--show-current"]  # pylint: disable=no-member
    output = exec_command(command)
    output.update({"REQUEST_PATH": "/current_branch"})
    response_400(output)
    current_branch = output.get("command_output", "").strip()

    data = {"branch": current_branch, "repo": str(app.repo_path)}
    response.update({"DATA": data})
    return response_200(response)


@app.get("/current_branch_internal", tags=["Branch Management"])
async def get_current_branch_internal():
    """
    # Summary

    Get the currently-set branch used internally in the running instance of the
    FastAPI application and is set using `/set_current_branch`.  If set, this
    overrides the current branch the repository is on, which is determined
    by the `git branch --show-current` command (see `/current_branch`).

    ## Example usage

    ### Command

    ```command
    curl 'http://127.0.0.1:8000/current_branch_internal'
    ```

    ### JSON Response

    - `DATA.branch`: The running FastAPI instance's internal branch (`app.repo_path`).
    - `DATA.repo`: The path to the repository.

    ```json response
    {
        "REQUEST_PATH":"/current_branch_internal",
        "REQUEST_METHOD":"GET",
        "DATA":{
            "branch":"dcnm-vrf-pydantic-integration",
            "repo":"/path/to/repo"
        },
        "STATUS_CODE":200
    }
    ```
    """
    if not app.repo_path:
        error_no_repo()
    response = {}
    response.update({"REQUEST_PATH": "/current_branch_internal"})
    response.update({"REQUEST_METHOD": "GET"})
    data = {}
    data["branch"] = app.branch
    data["repo"] = str(app.repo_path)
    response["DATA"] = data
    return response_200(response)


class GetCommitStatisticsParams(BaseModel):
    """
    Query parameter definitions for the `/commit_statistics` endpoint.
    """

    branch: Union[str | None] = Field(
        default=None,
        title="Branch Name",
        description="The name of the branch to query. This overrides the current branch set with `/set_branch`.",
        deprecated=False,
    )
    author: str = Field(default=None, title="Author", description="If provided, return only commits by this author.", deprecated=False)
    after: str = Field(
        default=None,
        title="After Date",
        description="If provided, return only commits after this date.",
        examples=["2025-01-01", "1 week ago"],
        deprecated=False,
    )
    before: str = Field(
        default=None,
        title="Before Date",
        description="If provided, return only commits before this date.",
        examples=["2025-07-01", "yesterday"],
        deprecated=False,
    )
    repo: str = Field(
        default=None,
        title="Repository Path",
        description="The absolute path to the repository.",
        deprecated=False,
    )


@app.get(
    "/commit_statistics",
    tags=["Repository Statistics"],
    # description="Get commit statistics (optionally filtered by author, branch, and date range) for the repository.",
)
async def get_commit_statistics(params: Annotated[GetCommitStatisticsParams, Query()]):
    """
    # Summary

    Get commit statistics (optionally filtered by author, branch, and date range) for the repository.

    ## Git Command

    ```bash
    git -C <repo_path> log --stat --author=<author> --after=<after_string> --before=<before_string> <branch>
    ```

    ## Example Git Command

    ```bash
    git -C /Users/arobel/repos/myrepo log --stat --author=arobel --after=2025-01-01 --before=2025-07-01 main
    ```


    Remember to URL encode the `after` and `before` query parameters if they contain spaces or special characters,
    but note that the Python `requests` library will handle this for you when you pass the parameters as a dictionary,
    so you only need to URL encode them if you are constructing the URL manually e.g. when using `curl`.

    E.g. replace spaces with `%20` or use `+` for spaces in URLs.

    For example, to search for commits after "1 week ago" and before today, use `after=1%20week%20ago&before=today`.

    ## Examples

    Find commits after July 1st 2024 and before today by author `arobel` on branch `dcnm-network-issue-395`.

    ### Command

    ```command
    curl 'http://127.0.0.1:8000/commit_statistics?before=today&after=July%201st%202024&author=arobel&branch=dcnm-network-issue-395'
    ```

    ### JSON Response

    ```json response
    {
        "REQUEST_PATH":"/commit_statistics",
        "REQUEST_METHOD":"GET",
        "DATA": {
            "commit_statistics": {
                "files": 689,
                "insertions": 75373,
                "deletions": 31696
            },
            "branch": "dcnm-network-issue-395"
        },
        "STATUS_CODE": 200
    }
    ```

    Same as above, but using `after` and `before` that do not need to be URL encoded since they do not contain spaces.

    ### Command

    ```command
    curl 'http://127.0.0.1:8000/commit_statistics?before=today&after=2024-07-01&author=arobel&branch=dcnm-network-issue-395'
    ```

    ### JSON Response

    ```json response
    {
        "REQUEST_PATH":"/commit_statistics",
        "REQUEST_METHOD":"GET",
        "DATA": {
            "commit_statistics": {
                "files": 689,
                "insertions": 75373,
                "deletions": 31696
            },
            "branch": "dcnm-network-issue-395"
        },
        "STATUS_CODE": 200
    }
    ```

    Same as above, but using the current branch (whatever that happens to be... notice the branch is different from the previous example).:

    ### Command

    ```command
    curl 'http://127.0.0.1:8000/commit_statistics?before=today&after=July%201st%202024&author=arobel'
    ```

    ### JSON Response

    ```json response
    {
        "REQUEST_PATH":"/commit_statistics",
        "REQUEST_METHOD":"GET",
        "DATA":{
            "commit_statistics":{
                "files":1110,
                "insertions":97213,
                "deletions":45256
            },
            "branch":"dcnm-vrf-pydantic-integration"
        },
        "STATUS_CODE":200
    }
    ```
    """
    # if not app.repo_path:
    #     error_no_repo()
    response = {}
    response.update({"REQUEST_PATH": "/commit_statistics"})
    response.update({"REQUEST_METHOD": "GET"})

    msg = f"get_commit_statistics(): params: {params}"
    app.log.debug(msg)

    if not params.repo and not app.repo_path:
        error_no_repo()
    if params.repo:
        app.repo_path = get_repo_path(params.repo)
        set_app_commands(app)
    command = app.log_stat_command.copy()  # pylint: disable=no-member
    if params.author:
        command.append(f"--author={params.author}")
    if params.after:
        command.append(f"--after={params.after}")
    if params.before:
        command.append(f"--before={params.before}")
    if params.branch:
        if not is_branch_in_repo(app, params.branch):
            error = f"Branch '{params.branch}' does not exist in the repository {app.repo_path}"
            response.update({"ERROR": error})
            response_400(response)

        msg = f"Using branch: {params.branch}"
        app.log.debug(msg)

        command.append(params.branch)
    elif app.branch:

        msg = f"Using previously-set branch: {app.branch}"
        app.log.debug(msg)

        command.append(app.branch)

    msg = f"git_commit_statistics(): command: {' '.join(command)}"
    app.log.debug(msg)

    response.update(exec_command(command))
    response_400(response)

    command_output = response.get("command_output", "")
    msg = f"command_output: {command_output}"
    app.log.debug(msg)

    files = 0
    insertions = 0
    deletions = 0
    for line in command_output.splitlines():
        msg = f"line: {line}"
        app.log.debug(msg)
        # 1 file changed, 5 insertions(+), 3 deletions(-)
        # 3 files changed, 294 insertions(+), 42 deletions(-)
        # 1 file changed, 14 insertions(+)
        # 1 file changed, 1 deletion(-)
        # match = re.search(r"^\s*(\d+)\s*file.* changed.*?(\d+)\s*insertions.*?(\d+)\s*deletions.*?$", line)
        match = re.search(r"^\s*(\d+)\s*file.* changed.*?$", line)
        if match:
            msg = f"Found {match.group(1)} files changed in line: {line}"
            app.log.debug(msg)
            files += int(match.group(1))
        match = re.search(r"^.*?(\d+)\s*insertions.*?$", line)
        if match:
            msg = f"Found {match.group(1)} insertions in line: {line}"
            app.log.debug(msg)
            insertions += int(match.group(1))
        match = re.search(r"^.*?(\d+)\s*deletions.*?$", line)
        if match:
            msg = f"Found {match.group(1)} deletions in line: {line}"
            app.log.debug(msg)
            deletions += int(match.group(1))

    msg = f"Files changed: {files}, Insertions: {insertions}, Deletions: {deletions}"
    app.log.debug(msg)

    data = {}
    data["commit_statistics"] = {
        "files": files,
        "insertions": insertions,
        "deletions": deletions,
        "author": params.author if params.author else None,
        "after": params.after if params.after else None,
        "before": params.before if params.before else None,
    }
    data["repo"] = str(app.repo_path)
    data["branch"] = params.branch if params.branch else current_branch_in_repo(app)
    response.update({"DATA": data})
    return response_200(response)


@app.post("/set_branch", tags=["Branch Management"])
async def set_current_branch(branch: str = None):
    """
    # Summary

    Set the current branch in the repository.

    # Example usage

    ```command
    curl -X POST 'http://127.0.0.1:8000/set_branch?branch=dev'
    ```
    ```json response
    {"REQUEST_PATH":"/set_branch","DATA":{"branch":"dev","repo":"/path/to/repo"},"STATUS_CODE":200}
    ```
    """
    if not app.repo_path:
        error_no_repo()
    if not branch:
        app.branch = None
    elif not is_branch_in_repo(app, branch):
        return {"error": f"Branch '{branch}' does not exist in the repository {app.repo_path}"}

    msg = f"Setting current branch to: {branch}"
    app.log.debug(msg)

    app.branch = branch

    response = {}
    data = {"branch": app.branch, "repo": str(app.repo_path)}
    response.update({"REQUEST_PATH": "/branch"})
    response.update({"REQUEST_METHOD": "POST"})
    response.update({"DATA": data})
    return response_200(response)


@app.post("/set_repo", tags=["Repository Management"])
async def set_current_repo(repo: str = None):
    """
    # Summary

    Set the path to the repository that will be queried.

    # Parameters

    ## `repo` (str): This can take two forms:

    - The absolute path to the repository as a string e.g. `/path/to/repo`.
      - If the path is not valid, a 400 error will be returned.
      - If the path is not a directory, a 400 error will be returned.
      - If the path does not exist, a 400 error will be returned.
    - The string "ENV" to use the environment variable `GITSTATS_REPO_PATH` e.g. `ENV`.
      - If the `GITSTATS_REPO_PATH` environment variable is not set, a 400 error will be returned.

    ## Example usage

    ### Command

    ```command
    curl -X POST 'http://127.0.0.1:8000/set_repo?repo=/path/to/repo'
    ```

    ### JSON Response

    ```json response
    {
        "REQUEST_PATH":"/set_repo",
        "REQUEST_METHOD":"POST",
        "DATA": {
            "repo":"/path/to/repo"
        },
        "STATUS_CODE":200
    }
    ```

    If the `repo` parameter is not provided, the repository path will be cleared.
    In this case, the application will not be able to execute any git commands
    and will return a 400 error for any endpoint that requires a repository path.
    Yes, we let you hang yourself.

    ### Command

    ```command
    curl -X POST 'http://127.0.0.1:8000/set_repo'
    ```

    ### JSON Response

    ```json response
    {
        "REQUEST_PATH":"/set_repo",
        "REQUEST_METHOD":"POST",
        "DATA":{"repo":null},
        "STATUS_CODE":200
    }
    ```

    If the `repo` parameter is set to "ENV", the value of the environment variable `GITSTATS_REPO_PATH` will be used.

    ### bash configuration

    ```bash
    export GITSTATS_REPO_PATH="/absolute/path/to/repo"
    ```

    ### Command

    ```command
    curl -X POST 'http://127.0.0.1:8000/set_repo?repo=ENV'
    ```

    ### JSON Response

    ```json response
    {
        "REQUEST_PATH":"/set_repo",
        "REQUEST_METHOD":"POST",
        "DATA":{"repo":"/absolute/path/to/repo"},
        "STATUS_CODE":200
    }
    ```
    """
    response = {}
    response["REQUEST_PATH"] = "/set_repo"
    response["REQUEST_METHOD"] = "POST"
    response["DATA"] = {}
    response["DATA"]["repo"] = repo
    if not repo:
        app.repo_path = None
        return response_200(response)
    repo_path = get_repo_path(repo=repo)

    msg = f"Setting app.repo_path to: {repo_path}"
    app.log.debug(msg)

    app.repo_path = repo_path
    set_app_commands(app)
    response["DATA"]["repo"] = str(app.repo_path)
    return response_200(response)
