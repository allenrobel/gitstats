import requests

def set_repo_path(repo):
    """
    Set the path to the Git repository.

    :param repo: Absolute path to the Git repository.
    """
    url = f"http://localhost:8000/set_repo?repo={repo}"
    requests.post(url)
