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

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field


class GitStatsLogger:
    """Logger class for the GitStats application."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)


class GitStatsConfig:
    """Configuration class for the GitStats application."""

    def __init__(self):
        self.repo_path: Path | None = None
        self.branch: str | None = None
        self.repo_command: list[str] = []
        self.log_command: list[str] = []
        self.log_stat_command: list[str] = []

    def set_repo_path(self, repo: str = None) -> Path | None:
        """
        Set the repository path.

        Args:
            repo: Repository path or "ENV" to use environment variable

        Returns:
            Path object representing the repository path

        Raises:
            HTTPException: If the repository path is invalid
        """
        if not repo:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing repo parameter.")

        if repo == "ENV":
            repo_path = os.environ.get("GITSTATS_REPO_PATH", None)
            if not repo_path:
                return None
        else:
            repo_path = repo

        # Ensure the repo path is absolute
        repo_path = Path(os.path.expanduser(repo_path)).resolve()
        if not repo_path.is_dir():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Repository path {repo_path} does not exist or is not a directory.")

        self.repo_path = repo_path
        self._set_commands()
        return repo_path

    def _set_commands(self):
        """Set the git command templates."""
        if self.repo_path:
            self.repo_command = ["git", "-C", str(self.repo_path)]
            self.log_command = self.repo_command + ["log"]
            self.log_stat_command = self.log_command + ["--stat"]


class GitCommandExecutor:
    """Class for executing git commands."""

    @staticmethod
    def execute(command: list[str]) -> dict:
        """
        Execute a shell command and return the output.

        Args:
            command: A list of strings representing the command and its arguments

        Returns:
            Dictionary with command output or error message
        """
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return {"command_output": result.stdout.strip()}
        except subprocess.CalledProcessError as e:
            return {"ERROR": e.stderr.strip()}


class GitRepositoryService:
    """Service class for git repository operations."""

    def __init__(self, config: GitStatsConfig, logger: GitStatsLogger):
        self.config = config
        self.logger = logger
        self.executor = GitCommandExecutor()

    def get_branches(self) -> list[str]:
        """Get the list of branches in the repository."""
        command = self.config.repo_command + ["branch", "--list"]
        output = self.executor.execute(command)
        if "ERROR" in output:
            return []

        command_output = output.get("command_output", "")
        branches = [line.strip() for line in command_output.splitlines() if line.strip()]
        # Remove leading '*' from the current branch
        branches = [line.lstrip("*").strip() for line in branches]
        return branches

    def is_branch_in_repo(self, branch: str) -> bool:
        """Check if a branch exists in the repository."""
        branches = self.get_branches()
        return branch in branches

    def get_current_branch(self) -> str:
        """Get the current branch in the repository."""
        if self.config.branch:
            self.logger.debug(f"Using previously-set branch: {self.config.branch}")
            return self.config.branch

        command = self.config.repo_command + ["branch", "--show-current"]
        output = self.executor.execute(command)
        if "ERROR" in output:
            return ""
        return output.get("command_output", "").strip()


class GitStatsService:
    """Main service class for git statistics operations."""

    def __init__(self, config: GitStatsConfig, logger: GitStatsLogger, repo_service: GitRepositoryService):
        self.config = config
        self.logger = logger
        self.repo_service = repo_service
        self.executor = GitCommandExecutor()

    def validate_repo_path(self):
        """Raise an HTTP 400 error if the repository path is not set."""
        if not self.config.repo_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repository path is not set. Use /set_repo to set the repository path.")

    def validate_branch(self, branch: str):
        """Validate that a branch exists in the repository."""
        if not self.repo_service.is_branch_in_repo(branch):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Branch '{branch}' does not exist in the repository {self.config.repo_path}")

    def create_response(self, path: str, method: str = "GET") -> dict:
        """Create a base response dictionary."""
        return {"REQUEST_PATH": path, "REQUEST_METHOD": method}

    def handle_error_response(self, response: dict):
        """Handle error responses by raising HTTPException if error is present."""
        if response.get("ERROR"):
            if not response.get("REQUEST_PATH"):
                response["REQUEST_PATH"] = "/unknown"
            if not response.get("REQUEST_METHOD"):
                response["REQUEST_METHOD"] = "UNKNOWN"
            response["STATUS_CODE"] = status.HTTP_400_BAD_REQUEST
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=response)

    def create_success_response(self, response: dict) -> dict:
        """Create a success response."""
        response.pop("command_output", None)
        response.update({"STATUS_CODE": status.HTTP_200_OK})
        return response


class GitStatsApplication:
    """Main application class that encapsulates all functionality."""

    def __init__(self):
        self.logger = GitStatsLogger()
        self.config = GitStatsConfig()
        self.repo_service = GitRepositoryService(self.config, self.logger)
        self.stats_service = GitStatsService(self.config, self.logger, self.repo_service)

        # Initialize repository path from environment
        try:
            self.config.set_repo_path("ENV")
        except HTTPException:
            # It's okay if the environment variable is not set
            pass

    def get_logger(self) -> GitStatsLogger:
        """Dependency function to get the logger."""
        return self.logger

    def get_config(self) -> GitStatsConfig:
        """Dependency function to get the configuration."""
        return self.config

    def get_repo_service(self) -> GitRepositoryService:
        """Dependency function to get the repository service."""
        return self.repo_service

    def get_stats_service(self) -> GitStatsService:
        """Dependency function to get the stats service."""
        return self.stats_service


# Global application instance
git_stats_app = GitStatsApplication()


# Dependency functions
def get_logger() -> GitStatsLogger:
    return git_stats_app.get_logger()


def get_config() -> GitStatsConfig:
    return git_stats_app.get_config()


def get_repo_service(config: GitStatsConfig = Depends(get_config), logger: GitStatsLogger = Depends(get_logger)) -> GitRepositoryService:
    return git_stats_app.get_repo_service()


def get_stats_service(
    config: GitStatsConfig = Depends(get_config), logger: GitStatsLogger = Depends(get_logger), repo_service: GitRepositoryService = Depends(get_repo_service)
) -> GitStatsService:
    return git_stats_app.get_stats_service()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the application."""
    logger = get_logger()
    config = get_config()

    logger.debug("Initializing GitStats API application...")
    msg = f"Repository path: {config.repo_path}"
    logger.debug(msg)
    yield


app = FastAPI(title="GitStats API", description="A FastAPI application for retrieving statistics from a Git repository.", version="1.0.0", lifespan=lifespan)


# Pydantic models for request parameters
class GetTopAuthorsParams(BaseModel):
    """Query parameter definitions for the `/top_authors` endpoint."""

    branch: Union[str | None] = Field(
        default=None,
        title="Branch Name",
        description="The name of the branch to query. This overrides the current branch set with `/set_branch`.",
        deprecated=False,
    )
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
    limit: int = Field(
        default=10,
        title="Number of Authors",
        description="Number of top authors to return (default: 10).",
        ge=1,
        le=100,
        deprecated=False,
    )
    repo: str = Field(
        default=None,
        title="Repository Path",
        description="The absolute path to the repository.",
        deprecated=False,
    )


class CommitCountParams(BaseModel):
    branch: Union[str | None] = Field(
        default=None,
        title="Branch Name",
        description="The name of the branch to query. This overrides the current branch set with `/set_branch`.",
        deprecated=False,
    )


class GetCommitStatisticsParams(BaseModel):
    """Query parameter definitions for the `/commit_statistics` endpoint."""

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


# API Endpoints
@app.get("/top_authors", tags=["Repository Statistics"])
async def get_top_authors(
    params: Annotated[GetTopAuthorsParams, Query()],
    stats_service: GitStatsService = Depends(get_stats_service),
    config: GitStatsConfig = Depends(get_config),
    logger: GitStatsLogger = Depends(get_logger),
    repo_service: GitRepositoryService = Depends(get_repo_service),
):
    """Get the top authors by commit count in the repository."""
    if not params.repo and not config.repo_path:
        stats_service.validate_repo_path()

    response = stats_service.create_response("/top_authors")

    if params.repo:
        config.set_repo_path(params.repo)

    # Build the git shortlog command
    command = config.repo_command + ["shortlog", "-sn"]

    if params.after:
        command.append(f"--after={params.after}")
    if params.before:
        command.append(f"--before={params.before}")

    if params.branch:
        stats_service.validate_branch(params.branch)
        logger.debug(f"Using branch: {params.branch}")
        command.append(params.branch)
    elif config.branch:
        logger.debug(f"Using previously-set branch: {config.branch}")
        command.append(config.branch)

    logger.debug(f"get_top_authors(): command: {' '.join(command)}")

    response.update(stats_service.executor.execute(command))
    stats_service.handle_error_response(response)

    command_output = response.get("command_output", "")

    # Parse the shortlog output
    authors = []
    for line in command_output.splitlines():
        line = line.strip()
        if line:
            match = re.match(r"^\s*(\d+)\s+(.+)$", line)
            if match:
                commit_count = int(match.group(1))
                author_name = match.group(2).strip()
                authors.append({"name": author_name, "commit_count": commit_count})

    # Limit the results
    top_authors = authors[: params.limit]
    total_authors = len(authors)

    logger.debug(f"Found {total_authors} authors, returning top {len(top_authors)}")

    data = {
        "top_authors": top_authors,
        "total_authors": total_authors,
        "branch": params.branch if params.branch else repo_service.get_current_branch(),
        "repo": str(config.repo_path),
        "limit": params.limit,
        "command": " ".join(command),
    }

    if params.after:
        data["after"] = params.after
    if params.before:
        data["before"] = params.before

    response.update({"DATA": data})
    return stats_service.create_success_response(response)


@app.get("/commit_count", tags=["Repository Statistics"])
async def get_commit_count(
    params: Annotated[CommitCountParams, Query()] = None,
    stats_service: GitStatsService = Depends(get_stats_service),
    config: GitStatsConfig = Depends(get_config),
    logger: GitStatsLogger = Depends(get_logger),
    repo_service: GitRepositoryService = Depends(get_repo_service),
):
    """Get the total number of commits in the repository."""
    stats_service.validate_repo_path()

    response = stats_service.create_response("/commit_count")
    command = config.repo_command + ["rev-list", "--count", "HEAD"]
    branch = None

    if params and params.branch:
        stats_service.validate_branch(params.branch)
        logger.debug(f"Using branch: {params.branch}")
        command.append(params.branch)
        branch = params.branch
    elif config.branch:
        logger.debug(f"Using previously-set branch: {config.branch}")
        command.append(config.branch)
        branch = config.branch

    logger.debug(f"command: {' '.join(command)}")
    output = stats_service.executor.execute(command)
    response.update({"command_output": output.get("command_output", "")})
    stats_service.handle_error_response(response)

    response.update(
        {
            "DATA": {
                "branch": branch,
                "command": " ".join(command),
                "commit_count": int(output.get("command_output")),
                "repo": str(config.repo_path),
            }
        }
    )
    return stats_service.create_success_response(response)


@app.get("/branches", tags=["Branch Management"])
async def get_branches(
    stats_service: GitStatsService = Depends(get_stats_service),
    config: GitStatsConfig = Depends(get_config),
    logger: GitStatsLogger = Depends(get_logger),
    repo_service: GitRepositoryService = Depends(get_repo_service),
):
    """Get the list of branches in the local repository."""
    stats_service.validate_repo_path()

    response = stats_service.create_response("/branches")
    command = config.repo_command + ["branch", "--list"]

    logger.debug(f"command: {' '.join(command)}")

    output = stats_service.executor.execute(command)
    command_output = output.get("command_output", "")
    response.update({"command_output": command_output})
    stats_service.handle_error_response(response)

    branches = repo_service.get_branches()
    data = {"branches": branches, "branch": repo_service.get_current_branch(), "command": " ".join(command), "repo": str(config.repo_path)}
    response.update({"DATA": data})
    return stats_service.create_success_response(response)


@app.get("/current_branch", tags=["Branch Management"])
async def get_current_branch(
    stats_service: GitStatsService = Depends(get_stats_service),
    config: GitStatsConfig = Depends(get_config),
    repo_service: GitRepositoryService = Depends(get_repo_service),
):
    """Return the branch that the repository is currently set to."""
    stats_service.validate_repo_path()

    response = stats_service.create_response("/current_branch")

    if config.branch:
        data = {"branch": config.branch, "repo": str(config.repo_path)}
        response.update({"DATA": data})
        return stats_service.create_success_response(response)

    command = config.repo_command + ["branch", "--show-current"]
    output = stats_service.executor.execute(command)
    output.update({"REQUEST_PATH": "/current_branch"})
    stats_service.handle_error_response(output)

    current_branch = output.get("command_output", "").strip()
    data = {"branch": current_branch, "repo": str(config.repo_path)}
    response.update({"DATA": data})
    return stats_service.create_success_response(response)


@app.get("/current_branch_internal", tags=["Branch Management"])
async def get_current_branch_internal(stats_service: GitStatsService = Depends(get_stats_service), config: GitStatsConfig = Depends(get_config)):
    """Get the currently-set branch used internally in the running instance."""
    stats_service.validate_repo_path()

    response = stats_service.create_response("/current_branch_internal")
    data = {"branch": config.branch, "repo": str(config.repo_path)}
    response["DATA"] = data
    return stats_service.create_success_response(response)


@app.get("/commit_statistics", tags=["Repository Statistics"])
async def get_commit_statistics(
    params: Annotated[GetCommitStatisticsParams, Query()],
    stats_service: GitStatsService = Depends(get_stats_service),
    config: GitStatsConfig = Depends(get_config),
    logger: GitStatsLogger = Depends(get_logger),
    repo_service: GitRepositoryService = Depends(get_repo_service),
):
    """Get commit statistics (optionally filtered by author, branch, and date range)."""
    if not params.repo and not config.repo_path:
        stats_service.validate_repo_path()

    response = stats_service.create_response("/commit_statistics")

    if params.repo:
        config.set_repo_path(params.repo)

    command = config.log_stat_command.copy()
    if params.author:
        command.append(f"--author={params.author}")
    if params.after:
        command.append(f"--after={params.after}")
    if params.before:
        command.append(f"--before={params.before}")
    if params.branch:
        stats_service.validate_branch(params.branch)
        logger.debug(f"Using branch: {params.branch}")
        command.append(params.branch)
    elif config.branch:
        logger.debug(f"Using previously-set branch: {config.branch}")
        command.append(config.branch)

    logger.debug(f"git_commit_statistics(): command: {' '.join(command)}")

    response.update(stats_service.executor.execute(command))
    stats_service.handle_error_response(response)

    command_output = response.get("command_output", "")

    files = 0
    insertions = 0
    deletions = 0
    for line in command_output.splitlines():
        match = re.search(r"^\s*(\d+)\s*file.* changed.*?$", line)
        if match:
            files += int(match.group(1))
        match = re.search(r"^.*?(\d+)\s*insertions.*?$", line)
        if match:
            insertions += int(match.group(1))
        match = re.search(r"^.*?(\d+)\s*deletions.*?$", line)
        if match:
            deletions += int(match.group(1))

    logger.debug(f"Files changed: {files}, Insertions: {insertions}, Deletions: {deletions}")

    data = {
        "commit_statistics": {
            "files": files,
            "insertions": insertions,
            "deletions": deletions,
            "author": params.author if params.author else None,
            "after": params.after if params.after else None,
            "before": params.before if params.before else None,
            "command": " ".join(command),
        },
        "repo": str(config.repo_path),
        "branch": params.branch if params.branch else repo_service.get_current_branch(),
    }
    response.update({"DATA": data})
    return stats_service.create_success_response(response)


@app.post("/set_branch", tags=["Branch Management"])
async def set_current_branch(
    branch: str = None,
    stats_service: GitStatsService = Depends(get_stats_service),
    config: GitStatsConfig = Depends(get_config),
    logger: GitStatsLogger = Depends(get_logger),
    repo_service: GitRepositoryService = Depends(get_repo_service),
):
    """Set the branch that will be queried by the application."""
    stats_service.validate_repo_path()

    if not branch:
        config.branch = None
    elif not repo_service.is_branch_in_repo(branch):
        return {"error": f"Branch '{branch}' does not exist in the repository {config.repo_path}"}

    logger.debug(f"Setting current branch to: {branch}")
    config.branch = branch

    response = stats_service.create_response("/branch", "POST")
    data = {"branch": config.branch, "repo": str(config.repo_path)}
    response.update({"DATA": data})
    return stats_service.create_success_response(response)


@app.post("/set_repo", tags=["Repository Management"])
async def set_current_repo(
    repo: str = None,
    stats_service: GitStatsService = Depends(get_stats_service),
    config: GitStatsConfig = Depends(get_config),
    logger: GitStatsLogger = Depends(get_logger),
):
    """Set the path to the repository that will be queried."""
    response = stats_service.create_response("/set_repo", "POST")
    response["DATA"] = {"repo": repo}

    if not repo:
        config.repo_path = None
        return stats_service.create_success_response(response)

    config.set_repo_path(repo=repo)
    logger.debug(f"Set repo_path to: {config.repo_path}")

    response["DATA"]["repo"] = str(config.repo_path)
    return stats_service.create_success_response(response)
