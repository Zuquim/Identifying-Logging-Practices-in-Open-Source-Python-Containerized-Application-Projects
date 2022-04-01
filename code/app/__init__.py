from logging import NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL

from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

default_logging_setup = dict(
    level=INFO,
    logfile="logs/app.log",
    maxBytes=1024000,
    backupCount=16,
)

logging_setup = dict(
    level=INFO,
    logfile="logs/app.log",
    fileLoglevel=DEBUG,
    maxBytes=1024000,
    backupCount=16,
)

# Setting up HTTPS Requests retry strategy
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504, 506],
    method_whitelist=["HEAD", "GET", "POST"],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
https = Session()
https.mount("https://", adapter)
