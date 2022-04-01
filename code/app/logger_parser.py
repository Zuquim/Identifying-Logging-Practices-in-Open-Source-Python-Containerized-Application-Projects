#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor
from csv import DictReader, DictWriter
from logging import DEBUG, INFO, WARNING
from os import chdir, listdir, walk
from os.path import exists
from re import match, search, sub
from time import time

from logzero import setup_logger

logging_setup = dict(
    name="logger_finder",
    level=INFO,
    logfile=f"/mnt/c/Users/mtuli/devel/python/tcc/logs/logger_finder(_).log",
    fileLoglevel=INFO,
    maxBytes=1024000,
    backupCount=16,
)
log = setup_logger(**logging_setup)

# Constants
columns = ("repo", "path", "line", "logger_object", "method", "verbosity", "level", "full_content", "len")
not_logger = ("console", "math", "np")
output_csv = "logger_calls6.csv"
regex_logger_verbosity_call = (
    r"^\s*(\w+\.)*"
    r"(?P<logger_object>\w+)"
    r"\."
    r"(?P<logger_verbosity>"
        r"([Ff][Aa][Tt][Aa][Ll])"
        r"|"
        r"([Cc][Rr][Ii][Tt]([Ii][Cc]([Aa][Ll])?)?)"
        r"|"
        r"([Ee][Xx][Cc][Ee][Pp][Tt]([Ii][Oo][Nn])?)"
        r"|"
        r"([Ee][Rr]{2}[Oo][Rr])"
        r"|"
        r"([Ww][Aa][Rr][Nn]([Ii][Nn][Gg])?)"
        r"|"
        r"([Ii][Nn][Ff][Oo])"
        r"|"
        r"([Dd][Ee][Bb][Uu][Gg])"
        r"|"
        r"([Ll][Oo][Gg])"
    r")\("
)
regex_logger_verbosity_call_complete = (
    r"^\s*(\w+\.)*"
    r"(?P<logger_object>\w+)"
    r"\."
    r"(?P<logger_verbosity>"
        r"([Ff][Aa][Tt][Aa][Ll])"
        r"|"
        r"([Cc][Rr][Ii][Tt]([Ii][Cc]([Aa][Ll])?)?)"
        r"|"
        r"([Ee][Xx][Cc][Ee][Pp][Tt]([Ii][Oo][Nn])?)"
        r"|"
        r"([Ee][Rr]{2}[Oo][Rr])"
        r"|"
        r"([Ww][Aa][Rr][Nn]([Ii][Nn][Gg])?)"
        r"|"
        r"([Ii][Nn][Ff][Oo])"
        r"|"
        r"([Dd][Ee][Bb][Uu][Gg])"
        r"|"
        r"([Ll][Oo][Gg])"
    r")"
    r"(?P<logger_content>\(.*\))"
    r"[\n\s]*$"
)

log_statement_counter = 0


def normalize_verbosity(verbosity: str) -> str:
    global log_statement_counter
    if match(r"[Dd][Ee][Bb][Uu][Gg]", verbosity):
        return "DEBUG"
    if match(r"[Ii][Nn][Ff][Oo]", verbosity):
        return "INFO"
    if match(r"[Ww][Aa][Rr][Nn]([Ii][Nn][Gg])?", verbosity):
        return "WARNING"
    if match(r"([Ee][Xx][Cc][Ee][Pp][Tt]([Ii][Oo][Nn])?)|([Ee][Rr]{2}[Oo][Rr])", verbosity):
        return "ERROR"
    if match(r"([Ff][Aa][Tt][Aa][Ll])|([Cc][Rr][Ii][Tt]([Ii][Cc]([Aa][Ll])?)?)", verbosity):
        return "CRITICAL"
    if match(r"[Ll][Oo][Gg]", verbosity):
        log_statement_counter += 1
        return "log"
    return "OTHER"


def get_verbosity_level(verbosity: str) -> int:
    return {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
        "OTHER": 99
    }[verbosity]


def guess_verbosity(content: str) -> str:
    if verbosity_match := search(
        r".*(?P<logger_verbosity>([Ff][Aa][Tt][Aa][Ll])|([Cc][Rr][Ii][Tt]([Ii][Cc]([Aa][Ll])?)?)|([Ee][Xx][Cc][Ee][Pp][Tt]([Ii][Oo][Nn])?)|([Ee][Rr]{2}[Oo][Rr])|([Ww][Aa][Rr][Nn]([Ii][Nn][Gg])?)|([Ii][Nn][Ff][Oo])|([Dd][Ee][Bb][Uu][Gg])).*",
        content
    ):
        return normalize_verbosity(verbosity_match.group("logger_verbosity"))
    return "OTHER"


def split_match_groups(match_dict: dict, match_obj) -> dict:
    match_dict["logger_object"] = match_obj.group("logger_object")
    match_dict["full_content"] = sub(r"\(\s*(.+)\s*\)", r"\1", match_obj.group("logger_content"))
    # match_dict["full_content"] = sub(r"[\'\"]\.format\([^\)]\)", "", match_dict["full_content"])
    match_dict["method"] = match_obj.group("logger_verbosity").lower()
    match_dict["verbosity"] = normalize_verbosity(match_dict["method"])
    if match_dict["verbosity"] == "log":
        match_dict["verbosity"] = guess_verbosity(match_dict["full_content"])
    match_dict["level"] = get_verbosity_level(match_dict["verbosity"])
    return match_dict


def check_logger_statement(match_dict: dict) -> bool:
    return False if match_dict["logger_object"] in not_logger or len(match_dict["full_content"]) < 2 else True


def logger_finder(path: str) -> list:
    repo = f"{path.split('/')[0]}/{path.split('/')[1]}"

    got_it = ""
    loggers = []
    match_dict = {}
    
    def reset_loop_mem():
        nonlocal got_it, loggers, match_dict
        got_it = ""
        match_dict = {}
    
    def open_stream(path: str):
        f = open(path)
        for line in f:
            yield line
        f.close()

    stream = open_stream(path)
    for i, line in enumerate(stream):
        if got_it == "" and not ( call_match := search(regex_logger_verbosity_call, line) ):
            # log.debug(f"#{i}".rjust(7, " ") + " | Skipped")
            continue

        if got_it == "" and match_dict == {} and call_match:
            got_it = sub(r"\s+", " ", sub(r"\n$", "", line))
            match_dict = dict(repo=repo, path=path, line=i)
            if ( full_match := search(regex_logger_verbosity_call_complete, line) ):
                log.debug(f"{repo} | {path}:{i} | Full: {got_it}")
                if check_logger_statement(logger_statement := split_match_groups(match_dict, full_match)):
                    loggers.append(logger_statement)
                reset_loop_mem()
                continue
            
            log.debug(f"{repo} | {path}:{i} | Partial: {got_it}")
            continue

        if got_it and match_dict:
            got_it += sub(r"\s+", " ", sub(r"\n$", "", line))
            if search(r"\)[\s\n]*$", line):
                if ( full_match := search(regex_logger_verbosity_call_complete, got_it) ):
                    log.debug(f"{repo} | {path}:{i} | Final: {got_it}")
                    if check_logger_statement(logger_statement := split_match_groups(match_dict, full_match)):
                        loggers.append(logger_statement)
                    reset_loop_mem()
                    continue

            log.debug(f"{repo} | {path}:{i} | Partial: {got_it}")
            continue

        log.error(f"{repo} | {path}:{i} | Something went wrong: i={i}; line='{line}'; match_dict={match_dict}; got_it='{got_it}'")
    
    log.debug(f"{repo} | {path} | logger calls: {len(loggers)}")
    return loggers


def get_paths(top: str = ".") -> str:
    for root, _, filenames in walk(top, topdown=True):
        for file_ in filenames:
            path = f"{root}/{file_}"
            if path.endswith(".py"):
                yield path


def main(repo: str):
    global log
    logging_setup = dict(
        name="logger_finder:{repo}",
        level=INFO,
        logfile=f"/mnt/c/Users/mtuli/devel/python/tcc/logs/logger_finder({repo.replace('/', '__')}).log",
        fileLoglevel=INFO,
        maxBytes=1024000,
        backupCount=16,
    )
    log = setup_logger(**logging_setup)

    log.info(f"Began: {repo}")

    paths = get_paths(repo)
    with ThreadPoolExecutor(max_workers=60) as ex:
        mapped_loggers = ex.map(logger_finder, paths)
    
    with open(f"/mnt/c/Users/mtuli/devel/python/tcc/output/{output_csv}", "a", encoding="utf-8", newline="") as f:
        csv = DictWriter(f=f, fieldnames=columns)
        try:
            for path in list(mapped_loggers):
                [csv.writerow(row) for row in path]
        except UnicodeDecodeError as e:
            log.error(f"{repo} | UnicodeDecodeError: {e}")

    log.info(f"Ended: {repo}")


if __name__ == "__main__":
    start_moment = time()
    repos_done = []
    chdir("/mnt/c/github_repos")

    # Reset CSV
    with open(f"/mnt/c/Users/mtuli/devel/python/tcc/output/{output_csv}", "w", encoding="utf-8", newline="") as f:
        csv = DictWriter(f=f, fieldnames=columns)
        csv.writeheader()

    # # Load CSV checkpoint
    # with open(f"/mnt/c/Users/mtuli/devel/python/tcc/output/{output_csv}", "r", encoding="utf-8", newline="") as f:
    #     csv = DictReader(f=f, fieldnames=columns)
    #     for row in csv:
    #         repos_done.append(row["repo"])
    # repos_done = list(dict.fromkeys(repos_done))

    with open(f"/mnt/c/Users/mtuli/devel/python/tcc/output/selected_repos") as f:  # Alphabetical
    # with open("/mnt/c/Users/mtuli/devel/python/tcc/output/selected_repos_r") as f:  # Reverse order
        repos = f.read()

    try:
        for repo in repos.splitlines():
            if repo in repos_done:
                log.warning(f"Skipping: {repo}")
                continue
            main(repo)
    except KeyboardInterrupt as e:
        log.warning(" ---- INTERRUPTED BY USER ---- ")
        quit()
    except Exception as e:
        log.exception(f"Exception: {e}")
        quit()
    finally:
        log.info(f"Number of 'log' statements: {log_statement_counter}")
        log.info(f"Time spent: {time() - start_moment:.3f} seconds")
