# Description

gitstats is a FastAPI application that provides statistics on Git repositories, such as commit counts, and commit statistics.

## Usage

1. cd /Path/where/I/keep/my/repos
2. git clone https://github.com/allenrobel/gitstats.git
3. cd gitstats
4. python -m venv .venv 
5. source .venv/bin/activate
6. pip install --upgrade pip
7. pip install -r requirements.txt
8. fastapi run app/main.py

After the above steps, you'll have a FastAPI app running and exposing its services at http://localhost:8000

In a separate terminal:

9. cd /Path/where/I/keep/my/repos/gitstats
10. source .venv/bin/activate
11. cd scripts
12. Edit one of the example scripts to match your repo (documentation provided in the script).
13. Run the script (e.g. python commit_statistics.py)

## Example script output

### Command

```bash
(venv.313)% python commit_statistics.py
```

### Output

```json
{
    "REQUEST_PATH": "/commit_statistics",
    "REQUEST_METHOD": "GET",
    "DATA": {
        "commit_statistics": {
            "files": 116,
            "insertions": 2166,
            "deletions": 658
        },
        "repo": "/Users/arobel/repos/wip",
        "branch": "main"
    },
    "STATUS_CODE": 200
}
```

## Using a web browser

Paste the following URL into a web browser.

http://localhost:8000/docs

This will display the documentation for the application's endpoints.

You can access the applications endpoints in a browser as well e.g.:


http://localhost:8000/commit_statistics?branch=main&after=2025-01-01&before=today&author=arobel

