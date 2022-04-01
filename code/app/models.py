from dataclasses import dataclass
from typing import Optional

from logzero import setup_logger

from app import logging_setup, https

# Setting up logger object
log = setup_logger(name="models", **logging_setup)


class GQL:
    class PageInfo:
        has_next_page = False
        end_cursor = "null"

    def __init__(self, headers, endpoint="https://api.github.com/graphql"):
        self.paging = GQL.PageInfo()
        self.__endpoint = endpoint
        self.__headers = headers
        self.__query = ""
        self.__query_template = ""
        self.__query_results = {}
        # self.__template_name = ""
        self.__template_path = "app/queries"
        self.__template_variables = dict(
            AFTER_CURSOR=f"after: {self.paging.end_cursor}",
            STARS_FILTER=f"stars:>1"
        )

    @property
    def endpoint(self):
        return self.__endpoint

    @property
    def headers(self):
        return self.__headers

    def set_headers(self, headers):
        if type(headers) is dict:
            self.__headers = headers
        else:
            log.error(f"{self.__class__}.set_headers(): headers must be a dict")

    @property
    def query(self):
        return self.__query

    def set_query(self, query):
        if type(query) is str:
            self.__query = query
        else:
            log.error(f"{self.__class__}.set_query(): query must be a str")

    @property
    def query_results(self):
        return self.__query_results

    def set_query_results(self, results_json):
        if type(results_json) is dict:
            if "pageInfo" in results_json["data"]["search"]:
                paging = results_json["data"]["search"]["pageInfo"]
                self.paging.has_next_page = paging["hasNextPage"]
                self.paging.end_cursor = f'"{paging["endCursor"]}"'
            self.__query_results = results_json["data"]["search"]
        else:
            log.error(
                f"{self.__class__}.set_query_results(): "
                f"results_json value must be a dict"
            )

    @property
    def query_template(self):
        return self.__query_template

    @property
    def template_path(self):
        return self.__template_path

    @property
    def template_variables(self):
        return self.__template_variables

    def set_template_variables(self, **kwargs):
        self.__template_variables = kwargs

    def load_query(self, template_name):
        template = self._load_query_template(template_name, self.__template_path)
        self.set_query(self._setup_query(template, self.template_variables))

    def reload_query(self):
        if self.query_template:
            self.set_query(
                self._setup_query(self.query_template, self.template_variables)
            )

    def _load_query_template(self, template_name, template_path):
        with open(f"{template_path}/{template_name}") as f:
            self.__query_template = f.read()
        return self.query_template

    @staticmethod
    def _setup_query(query_template, var_dict):
        query = query_template
        for key in var_dict.keys():
            query = query.replace(f"<{key}>", var_dict[key])
        return query

    def run_query(self, retry=2, raw_response=False):
        for i in range(-1, retry):
            response = https.post(
                url=self.endpoint, headers=self.headers, json=dict(query=self.query)
            )
            if raw_response:
                return response
            if "X-RateLimit-Remaining" in response.headers:
                log.debug(
                    f"{self.__class__}.run_query({self.__hash__()}): "
                    f"X-RateLimit-Remaining={response.headers['X-RateLimit-Remaining']}"
                )
            else:
                log.debug(
                    f"{self.__class__}.run_query({self.__hash__()}): "
                    f"response[{response.status_code}].text={response.text}"
                )
            if response.status_code == 200:
                self.set_query_results(response.json())
                return self.query_results
            elif response.status_code == 403:
                log.debug(
                    f"{self.__class__}.run_query({self.__hash__()}): "
                    f"self.query={self.query}"
                )
                raise ConnectionRefusedError(
                    f"Triggered API abuse mechanism! (hash={self.__hash__()})"
                )
            log.warning(
                f"Query attempt #{i + 2} failed (status_code={response.status_code})"
            )
        log.error(f"Giving up on query (hash={self.__hash__()})")
        log.debug(
            f"{self.__class__}.run_query({self.__hash__()}): self.query={self.query})"
        )

    def next_page(self):
        if not self.paging.has_next_page:
            return False
        self.template_variables["AFTER_CURSOR"] = f"after:{self.paging.end_cursor}"
        self.reload_query()
        return self.run_query()


@dataclass
class Repo:
    id: str = ""
    ssh_url: str = ""
    created_at: str = ""
    updated_at: str = ""
    license_info_name: str = ""
    is_fork: Optional[bool] = None
    is_in_organization: Optional[bool] = None
    stargazers_total_count: int = -1
    watchers_total_count: int = -1
    forks_total_count: int = -1
    releases_total_count: int = -1
    commit_comments_total_count: int = -1
    collaborators_total_count: int = -1
    collaborators_direct_count: int = -1
    collaborators_outside_count: int = -1
    pull_requests_total_count: int = -1
    pull_requests_open_count: int = -1
    issues_total_count: int = -1
    issues_open_count: int = -1

    def setup_via_json(self, json):
        """
        json param must correspond to GQL query
        """
        if type(json) is dict:
            self.id = json["id"]
            self.ssh_url = json["sshUrl"]
            self.created_at = json["createdAt"]
            self.updated_at = json["updatedAt"]
            self.is_fork = json["isFork"]
            self.is_in_organization = json["isInOrganization"]
            if json["licenseInfo"]:
                self.license_info_name = json["licenseInfo"]["name"]
            self.stargazers_total_count = json["stargazers"]["totalCount"]
            self.watchers_total_count = json["watchers"]["totalCount"] if json["watchers"] else 0
            self.forks_total_count = json["forks"]["totalCount"] if json["forks"] else 0
            self.releases_total_count = json["releases"]["totalCount"] if json["releases"] else 0
            self.commit_comments_total_count = json["commitComments"]["totalCount"] if json["commitComments"] else 0
            self.collaborators_total_count = json["collaborators"]["totalCount"] if json["collaborators"] else 0
            self.collaborators_direct_count = json["collaboratorsDirect"]["totalCount"] if json["collaboratorsDirect"] else 0
            self.collaborators_outside_count  = json["collaboratorsOutside"]["totalCount"] if json["collaboratorsOutside"] else 0
            self.pull_requests_total_count = json["pullRequests"]["totalCount"] if json["pullRequests"] else 0
            self.pull_requests_open_count = json["pullRequestsOpen"]["totalCount"] if json["pullRequestsOpen"] else 0
            self.issues_total_count = json["issues"]["totalCount"] if json["issues"] else 0
            self.issues_open_count = json["issuesOpen"]["totalCount"] if json["issuesOpen"] else 0

        else:
            log.error(f"{self.__class__}.setup_via_json(): json must be a dict")

    def export_repo_info_as_json(self):
        return dict(
            id=self.id,
            ssh_url=self.ssh_url,
            created_at=self.created_at,
            updated_at=self.updated_at,
            stars=self.stargazers_total_count,
            license=self.license_info_name,
            is_fork=self.is_fork,
            in_org=self.is_in_organization,
            watchers=self.watchers_total_count,
            forks=self.forks_total_count,
            releases=self.releases_total_count,
            commit_comments=self.commit_comments_total_count,
            collaborators=self.collaborators_total_count,
            collab_direct=self.collaborators_direct_count,
            collab_outside=self.collaborators_outside_count,
            prs=self.pull_requests_total_count,
            prs_open=self.pull_requests_open_count,
            issues=self.issues_total_count,
            issues_open=self.issues_open_count,
        )


class Repository:
    def __init__(self):
        self.__id = ""
        self.__owner = ""
        self.__name = ""
        self.__url = ""
        self.__created_at = ""
        self.__updated_at = ""
        self.__primary_language_name = ""
        # self.__license = None
        self.__license_info_name = ""
        # self.__stargazers = []
        self.__stargazers_total_count = -1
        # self.__watchers = []
        self.__watchers_total_count = -1
        # self.__forks = []
        self.__forks_total_count = -1
        # self.__releases = []
        self.__releases_total_count = -1
        self.__pull_requests = []
        self.__pull_requests_total_count = -1
        self.__pull_requests_open_count = -1
        # self.__issues = []
        self.__issues_total_count = -1
        self.__issues_open_count = -1
        self.__issues_open_old_count = -1

    @property
    def id(self):
        return self.__id

    def set_id(self, id):
        self.__id = id

    @property
    def owner(self):
        return self.__owner

    def set_owner(self, owner):
        if type(owner) is str:
            self.__owner = owner
        else:
            log.error(f"{self.__class__}.set_owner(): owner must be a str")

    @property
    def name(self):
        return self.__name

    def set_name(self, name):
        if type(name) is str:
            self.__name = name
        else:
            log.error(f"{self.__class__}.set_name(): name must be a str")

    @property
    def name_with_owner(self):
        return f"{self.owner}/{self.name}"

    @property
    def url(self):
        return self.__url

    def set_url(self, url):
        if type(url) is str:
            self.__url = url
        else:
            log.error(f"{self.__class__}.set_url(): url must be a str")

    @property
    def created_at(self):
        return self.__created_at

    def set_created_at(self, created_at):
        self.__created_at = created_at

    @property
    def updated_at(self):
        return self.__updated_at

    def set_updated_at(self, updated_at):
        self.__updated_at = updated_at

    @property
    def primary_language_name(self):
        return self.__primary_language_name

    def set_primary_language_name(self, language_name):
        if type(language_name) is str:
            self.__primary_language_name = language_name
        else:
            log.error(
                f"{self.__class__}.set_primary_language_name(): "
                f"language_name must be a str"
            )

    @property
    def license_info_name(self):
        return self.__license_info_name

    def set_license_info_name(self, license_name):
        if type(license_name) is str:
            self.__license_info_name = license_name
        else:
            log.error(
                f"{self.__class__}.set_license_info_name():"
                f"license_name must be a str"
            )

    @property
    def stargazers_total_count(self):
        return self.__stargazers_total_count

    def set_stargazers_total_count(self, stargazers_count):
        if type(stargazers_count) is int and stargazers_count >= 0:
            self.__stargazers_total_count = stargazers_count
        else:
            log.error(
                f"{self.__class__}.set_stargazers_total_count(): "
                f"stargazers_count must be an int >=0"
            )

    @property
    def forks_total_count(self):
        return self.__forks_total_count

    def set_forks_total_count(self, forks_count):
        if type(forks_count) is int and forks_count >= 0:
            self.__forks_total_count = forks_count
        else:
            log.error(
                f"{self.__class__}.set_forks_total_count(): "
                f"forks_count must be an int >=0"
            )

    @property
    def releases_total_count(self):
        return self.__releases_total_count

    def set_releases_total_count(self, releases_count):
        if type(releases_count) is int and releases_count >= 0:
            self.__releases_total_count = releases_count
        else:
            log.error(
                f"{self.__class__}.set_releases_total_count(): "
                f"releases_count must be an int >=0"
            )

    @property
    def pull_requests(self):
        return self.__pull_requests

    def set_pull_requests(self, pr_list):
        self.__pull_requests = pr_list

    @property
    def pull_requests_total_count(self):
        return self.__pull_requests_total_count

    def set_pull_requests_total_count(self, pull_requests_count):
        if type(pull_requests_count) is int and pull_requests_count >= 0:
            self.__pull_requests_total_count = pull_requests_count
        else:
            log.error(
                f"{self.__class__}.set_pull_requests_total_count(): "
                f"pull_requests_count must be an int >=0"
            )

    @property
    def pull_requests_open_count(self):
        return self.__pull_requests_open_count

    def set_pull_requests_open_count(self, pull_requests_count):
        if type(pull_requests_count) is int and pull_requests_count >= 0:
            self.__pull_requests_open_count = pull_requests_count
        else:
            log.error(
                f"{self.__class__}.set_pull_requests_open_count(): "
                f"pull_requests_count must be an int >=0"
            )

    @property
    def issues_total_count(self):
        return self.__issues_total_count

    def set_issues_total_count(self, issues_count):
        if type(issues_count) is int and issues_count >= 0:
            self.__issues_total_count = issues_count
        else:
            log.error(
                f"{self.__class__}.set_issues_total_count(): "
                f"issues_count must be an int >=0"
            )

    @property
    def issues_open_count(self):
        return self.__issues_open_count

    def set_issues_open_count(self, issues_count):
        if type(issues_count) is int and issues_count >= 0:
            self.__issues_open_count = issues_count
        else:
            log.error(
                f"{self.__class__}.set_issues_open_count(): "
                f"issues_count must be an int >=0"
            )

    @property
    def issues_open_old_count(self):
        return self.__issues_open_old_count

    def set_issues_open_old_count(self, issues_count):
        if type(issues_count) is int and issues_count >= 0:
            self.__issues_open_old_count = issues_count
        else:
            log.error(
                f"{self.__class__}.set_issues_open_old_count(): "
                f"issues_count must be an int >=0"
            )

    def setup_via_json(self, json):
        """
        json param must correspond to queries/top_python_repositories.gql GQL query
        """
        if type(json) is dict:
            self.set_owner(json["nameWithOwner"].split("/")[0])
            self.set_name(json["nameWithOwner"].split("/")[1])
            self.set_url(json["url"])
            self.set_stargazers_total_count(json["stargazers"]["totalCount"])
            # if json["primaryLanguage"]:
            #     self.set_primary_language_name(json["primaryLanguage"]["name"])
        else:
            log.error(f"{self.__class__}.setup_via_json(): json must be a dict")

    def export_repo_info_as_json(self):
        return dict(
            repo=self.name_with_owner,
            url=self.url,
            stars=self.stargazers_total_count,
        )


def repository(node_json):
    repo = Repository()
    repo.setup_via_json(node_json)
    return repo
    

def repo_dataclass(node_json):
    repo = Repo()
    repo.setup_via_json(node_json)
    return repo
