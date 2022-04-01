from csv import DictReader, DictWriter
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from json import dumps
from os import getenv, rmdir, makedirs, system
from os.path import exists
from time import sleep, time
from typing import List, Optional, Union

from git import Git
from git.exc import GitCommandError
from logzero import setup_logger

from app import logging_setup, https
from app.models import GQL, Repository, repository

log = setup_logger(name="data_ingestion", **logging_setup)

_csv_file = "logs/python_top_repositories-01.csv"
_repos_file = "logs/repos_{letter}.csv"
_csv_fieldnames = ["repo", "url", "stars"]
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


def read_csv(csv_file: str = _csv_file):
    with open(csv_file, encoding="utf-8", newline="") as f:
        csv = DictReader(f=f)
        for row in csv:
            yield row["repo"], row["url"], row["stars"]


def read_csv_selected(csv_file: str = _csv_file):
    with open(csv_file, encoding="utf-8", newline="") as f:
        csv = DictReader(f=f)
        for row in csv:
            if not row["selected"]:
                continue
            yield row["repo"], row["url"], row["stars"], row["status"]


def query_top_python_repositories(stars_filter: Optional[str] = None):  # FIXME: set stars_filter = None
    """
    stars_filter examples:
    >7
    <42
    42..420
    """
    log.info("Querying top popular Python GitHub repositories...")
    gql = GQL(endpoint=endpoint, headers=headers)
    gql.load_query("top_python_repositories.gql")
    if stars_filter:
        gql.set_template_variables(
            AFTER_CURSOR=f"after: {gql.paging.end_cursor}",
            STARS_FILTER=f"stars:{stars_filter}"
        )
        gql.reload_query()
    run = 1
    try:
        gql.run_query()
    except ConnectionRefusedError as e:
        log.error(e)
        return
    log.debug(
        f"query_top_python_repositories(): "
        f'repositoryCount={gql.query_results["repositoryCount"]} {{'
    )
    if "nodes" in gql.query_results and gql.query_results["nodes"]:
        append_to_csv([repository(node) for node in gql.query_results["nodes"]])
        while gql.paging.has_next_page:
            run += 1
            log.info(f"Running query #{run} (pageID: {gql.paging.end_cursor})")
            try:
                gql.next_page()
            except ConnectionRefusedError as e:
                log.error(e)
            else:
                append_to_csv([repository(node) for node in gql.query_results["nodes"]])
    log.debug(
        f"}} query_top_python_repositories(): "
        f'repositoryCount={gql.query_results["repositoryCount"]}'
    )


def query_top_python_repositories_details(repo: str):
    log.info(f"Querying: {repo}")
    gql = GQL(endpoint=endpoint, headers=headers)
    gql.load_query("python_repos_details.gql")
    gql.set_template_variables(REPO__OWNER_NAME=f"repo: {repo}")
    gql.reload_query()
    try:
        gql.run_query()
    except ConnectionRefusedError as e:
        log.error(e)
        return

    if "nodes" in gql.query_results and gql.query_results["nodes"]:
        append_to_csv([repository(node) for node in gql.query_results["nodes"]])
    else:
        log.error(f"Repository not found: {repo}")
    log.info(f"Done with {repo}")


def make_repo_dir(repo_name: str) -> str:
    owner = repo_name.split("/")[0]
    repo = repo_name.split("/")[1]
    repo_path = _repos_path + f"/{owner}"
    if not exists(repo_path):
        makedirs(repo_path)
    return repo_path


# def clone_repo(name: str, url: str):
def clone_repo(csv_yield: tuple):
    name = csv_yield[0]
    url = csv_yield[1]
    stars = csv_yield[2]
    try:
        Git(make_repo_dir(name)).clone(f"{url.replace('https', 'git')}.git")
    except GitCommandError as e:
        if "Repository not found." in str(e):
            log.error(f"{name} | {stars} | Repository not found!")
            return 404
        elif "Please make sure you have the correct access rights" in str(e):
            log.error(f"{name} | {stars} | Repository access is restricted!")
            return 403
        elif " already exists and is not an empty directory." in str(e):
            log.warning(f"{name} | {stars} | Repository directory already exists and it's not empty.")
            return 409
        else:
            log.exception(f"{name} | {stars} | Unidentified error! | {e}")
            return 500
    else:
        log.info(f"{name} | {stars} | Repository cloned!")
        return 200


def look_for_msa_clue():
    # https://api.github.com/repos/owner/repo_name/git/trees/master?recursive=1
    # iterate JSON from call above
    # if MSA clue found, return True
    # else check if is truncated (if it is, clone it), else False
    pass


# Defining request parameters
endpoint = "https://api.github.com/graphql"
headers = {
    "Accept": "application/vnd.github.v4.idl",
    "Authorization": f"bearer {read_github_token_env()}",
}


def get_repos_csv(stars_range: Optional[str]):  # "10..200"
    if not exists(_csv_file):
        new_csv()
    query_top_python_repositories(stars_filter=stars_range)


def clone_all(letter: str):
    with ThreadPoolExecutor(max_workers=10) as ex:
        return_codes = ex.map(clone_repo, read_csv(_repos_file.format(letter=letter)))
    for i, status in enumerate(list(return_codes)):
        print(i, status)
    system("st Done!")


def main():
    # Getting 50 most popular repositories from GitHub
    # response_repos = query_top_python_repositories()

    new_csv()
    query_top_python_repositories(stars_filter="150..1730")

    with ThreadPoolExecutor(max_workers=50) as ex:
        return_codes = ex.map(clone_repo, read_csv())
    for i, status in enumerate(list(return_codes)):
        print(i, status)
    system("st Done!")

    # # Organizing the repositories in a list of Repository objects
    # repository_list = []
    # for node in response_repos:
    #     repository_list.append(repository(node))
    #
    # # Mapping Pull Requests for each repository in the list
    # log.info(f"Querying open PullRequests from top 50 repositories...")
    # with ThreadPoolExecutor(max_workers=10) as ex:
    #     repos_w_prs_map = ex.map(query_top_python_repositories, repository_list)
    # repos_w_prs = list(repos_w_prs_map)
    #
    # # Dumping JSON data from Repository and PullRequest object lists
    # for repo in list(repos_w_prs):
    #     print(dumps(repo.export_repo_info_as_json()))
    #     for pr in repo.pull_requests:
    #         print(dumps(pr.export_pullrequest_info_as_json()))


if __name__ == "__main__":
    starttime = time()
    # TODO: mkdir logs dir
    # Loading GitHub token manually
    # if not _token:
    #     _token = read_github_token_input()

    try:
        # get_repos_csv(None)
        # get_repos_csv("1743..3136")
        # get_repos_csv("1100..1743")
        # get_repos_csv("900..1194")
        # get_repos_csv("700..904")
        # get_repos_csv("600..723")
        # get_repos_csv("500..603")
        # get_repos_csv("450..518")
        # get_repos_csv("400..452")
        # get_repos_csv("360..401")
        # get_repos_csv("300..360")
        clone_all("M")
    except KeyboardInterrupt:
        log.warning("Execution interrupted by user (^C)")
        print(f"\nExecution interrupted via ^C " f"at {time() - starttime:.2f}s")

    log.info(f"Total execution time: {time() - starttime:.2f}s")
