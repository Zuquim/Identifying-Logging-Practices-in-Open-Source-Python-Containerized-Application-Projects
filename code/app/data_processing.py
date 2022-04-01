from csv import DictReader, DictWriter
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from json import dumps, dump, load
from os import getenv, rmdir, makedirs, system
from os.path import exists
from random import uniform
from time import sleep, time
from typing import List, Optional, Union

from logzero import setup_logger

from app import logging_setup, https
from app.models import GQL, Repository, repo_dataclass

log = setup_logger(name="repo_details", **logging_setup)

read_csv_file = "output/bulk_.csv"
_csv_file = "output/bulk_updated.csv"
_csv_fieldnames = ["id", "repo", "url", "ssh_url", "created_at", "updated_at", "is_fork", "in_org", "stars", "watchers", "forks", "releases", "commit_comments", "collaborators", "collab_direct", "collab_outside", "contributors", "prs", "prs_open", "issues", "issues_open", "license", "status", "selected", "lloc", "dockerfile", "docker-compose", ".kube", "configmap", "logging", "daiquiri", "eliot", "logbook", "loguru", "logzero", "pysimplelog", "structlog", "twiggy"]
_repos_path = "/mnt/godzilla/github_repos"


def check_github_token(token_str: str):
    expected_token_length = 40
    if len(token_str) == expected_token_length:
        return token_str

    error_msg = (
        f"Provided token length ("
        f"{len(token_str)}) does not match "
        f"expected length ({expected_token_length})!"
    )
    log.error(error_msg)
    raise ValueError(error_msg)


def read_github_token_env(env: str = "GITHUB_TOKEN"):
    return check_github_token(getenv(env))


def read_github_token_input(token_str: str = ""):
    if not token_str:
        log.info("Reading token string from user input...")
        token_str = input("Insert GitHub token string: ")
    return check_github_token(token_str.strip())


def new_csv():
    with open(_csv_file, "w", encoding="utf-8", newline='') as f:
        csv = DictWriter(f, fieldnames=_csv_fieldnames, )
        csv.writeheader()


def append_to_csv(data: List[Repository]):
    with open(_csv_file, "a", encoding="utf-8", newline='') as f:
        csv = DictWriter(f, fieldnames=_csv_fieldnames)
        csv.writerows([r.export_repo_info_as_json() for r in data])


def read_csv(csv_file: str = read_csv_file):
    with open(csv_file, encoding="utf-8", newline="") as f:
        csv = DictReader(f=f)
        for row in csv:
            yield row


def read_csv_selected(csv_file: str = read_csv_file):
    with open(csv_file, encoding="utf-8", newline="") as f:
        csv = DictReader(f=f)
        for row in csv:
            if "TRUE" not in row["selected"]:
                continue
            yield row


def write_to_csv(data: List[dict]):
    with open(_csv_file, "w", encoding="utf-8", newline='') as f:
        csv = DictWriter(f, fieldnames=_csv_fieldnames)
        csv.writeheader()
        csv.writerows(data)


def query_top_python_repositories_details(row: dict):
    if "TRUE" not in row["selected"]:
        return row

    repo = row["repo"]
    log.info(f"Querying: {repo}")
    sleep(uniform(2, 10))
    gql = GQL(endpoint=endpoint, headers=headers)
    gql.load_query("python_repos_details.gql")
    gql.set_template_variables(REPO__OWNER_NAME=f"repo:{repo}")
    gql.reload_query()

    try:
        gql.run_query()
    except ConnectionRefusedError as e:
        log.error(e)
        return row
    # else:
        # log.debug(f"{gql.query_results}")
        # log.debug(f"BEFORE: row={row}")

    if "nodes" in gql.query_results and len(gql.query_results["nodes"]) >= 1:
        repo_obj = repo_dataclass(gql.query_results["nodes"][0])
        rdc = repo_obj.export_repo_info_as_json()
        # log.warning(f"rdc={rdc}")
        row["id"] = rdc["id"]
        row["ssh_url"] = rdc["ssh_url"]
        row["created_at"] = rdc["created_at"]
        row["updated_at"] = rdc["updated_at"]
        row["stars"] = rdc["stars"]
        row["watchers"] = rdc["watchers"]
        row["forks"] = rdc["forks"]
        row["is_fork"] = rdc["is_fork"]
        row["in_org"] = rdc["in_org"]
        row["license"] = rdc["license"]
        row["releases"] = rdc["releases"]
        row["commit_comments"] = rdc["commit_comments"]
        row["collaborators"] = rdc["collaborators"]
        row["collab_direct"] = rdc["collab_direct"]
        row["collab_outside"] = rdc["collab_outside"]
        row["prs"] = rdc["prs"]
        row["prs_open"] = rdc["prs_open"]
        row["issues"] = rdc["issues"]
        row["issues_open"] = rdc["issues_open"]
        log.info(f"Done with {repo}")
        # log.debug(f"AFTER: row={row}")
    else:
        log.error(f"Not found: {repo}")

    return row


# Defining request parameters
endpoint = "https://api.github.com/graphql"
headers = {
    "Accept": "application/vnd.github.v4.idl",
    "Authorization": f"bearer {read_github_token_env()}",
}


def main():
    new_csv()

    with ThreadPoolExecutor(max_workers=10) as ex:
        row_map = ex.map(query_top_python_repositories_details, read_csv())
    
    # query_top_python_repositories_details("")
    rows = list(row_map)

    log.info(f"number of rows: {len(rows)}")

    with open("temp.json", "w", encoding="utf-8") as f:
        dump(dict(repos=rows), fp=f)

    write_to_csv(rows)


if __name__ == "__main__":
    starttime = time()

    try:
        main()
    except KeyboardInterrupt:
        log.warning("Execution interrupted by user (^C)")
        print(f"\nExecution interrupted via ^C " f"at {time() - starttime:.2f}s")

    log.info(f"Total execution time: {time() - starttime:.2f}s")
