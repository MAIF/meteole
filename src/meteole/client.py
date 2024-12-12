"""Core module for the MeteoFranceClient package."""

import logging
import os
import tempfile
import time
from pathlib import Path

import requests

from meteole.const import (
    EXPIRED_TOKEN_CODE,
    MISSING_DATA_CODE,
    PARAMETER_ERROR_CODE,
    SPECIFIC_ERROR,
    SUCCESS_CODES,
)
from meteole.errors import MissingDataError, MissingParameterError

logger = logging.getLogger(__name__)


class MeteoFranceClient:
    """Handles the connection and token refreshment boilerplate"""

    def __init__(
        self,
        api_key: str | None = None,
        token: str | None = None,
        application_id: str | None = None,
    ):
        """Init the MeteoFranceClient object."""
        self.api_key = api_key
        self.token = token
        self.application_id = application_id

        self.session = requests.Session()
        self.connect()

    def connect(self):
        """Connect to the MeteoFrance API.

        If the API key is provided, it is used to authenticate the user.
        If the token is provided, it is used to authenticate the user.
        If the application ID is provided, a token is requested from the API.
        """
        if self.api_key is None and self.token is None:
            if self.application_id is None:
                raise ValueError("api_key or token or application_id must be provided")
            self.token = self.get_token()
        if self.api_key is not None:
            logger.debug("using api key")
            self.session.headers.update({"apikey": self.api_key})
        else:
            logger.debug("using token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def get_token(self):
        """request a token from the meteo-France API.

        The token lasts 1 hour, and is used to authenticate the user.
        If a new token is requested before the previous one expires, the previous one is invalidated.
        A local cache is used to avoid requesting a new token at each run of the script.
        """
        # cache the token for 1 hour
        TOKEN_DURATION_S = 3600
        local_tmp_cache = tempfile.TemporaryDirectory().name
        cache_filename = Path(local_tmp_cache) / "token.txt"
        cache_time_filename = Path(local_tmp_cache) / "token_time.txt"

        # try to read  from cache
        if cache_filename.exists() and cache_time_filename.exists():
            logger.debug("reading token from cache")
            with open(cache_time_filename) as f:
                cache_time = float(f.read())
            if cache_time >= (time.time() - TOKEN_DURATION_S):
                with open(cache_filename) as f:
                    token = f.read()
                return token

        token_entrypoint = "https://portail-api.meteofrance.fr/token"  # noqa: S105
        params = {"grant_type": "client_credentials"}
        header = {"Authorization": "Basic " + self.application_id}
        res = requests.post(token_entrypoint, params=params, headers=header, timeout=(30, 3600))
        self.token = res.json()["access_token"]

        # save token to file
        Path(local_tmp_cache).mkdir(parents=True, exist_ok=True)
        with open(cache_filename, "w") as f:
            f.write(self.token)
        with open(cache_time_filename, "w") as f:
            f.write(str(time.time()))
        return self.token

    def _get_request(self, url, params=None, max_retries=5):
        """Make a get request to the API.

        Parameters
        ----------
        url : str
            the url to request
        params : dict
            the parameters to pass to the request
        max_retries : int
            the maximum number of retries

        Returns
        -------
        requests.Response
            the response of the request
        """
        logger.debug(f"GET {url}")
        path_certif = str(Path(__file__).parents[0] / "utils/cacert.pem")
        attempt = 0
        while attempt < max_retries:
            if os.path.isfile(path_certif):
                res = self.session.get(url, params=params, verify=path_certif)
            else:
                res = self.session.get(url, params=params)
            if self._token_expired(res):
                logger.info("token expired, requesting a new one")
                self.get_token()
                self.connect()
                if os.path.isfile(path_certif):
                    res = self.session.get(url, params=params, verify=path_certif)
                else:
                    res = self.session.get(url, params=params)
                return res

            error_code = res.status_code
            if error_code in SUCCESS_CODES:
                logger.debug("request successful")
                return res
            if error_code == PARAMETER_ERROR_CODE:
                logger.error("parameter error")
                raise MissingParameterError(res.text)
            if error_code == MISSING_DATA_CODE:
                logger.error("missing data")
                raise MissingDataError(res.text)
            if error_code == SPECIFIC_ERROR:
                logger.error("Erreur code status 502")
                time.sleep(5)
                attempt += 1
                logger.info(f"Retrying... Attempt {attempt} of {max_retries}")
                continue

            break

        raise ValueError("Failed to get a successful response after retries")

    @staticmethod
    def _token_expired(res):
        """Check if the token is expired.

        Returns
        -------
        bool
            True if the token is expired, False otherwise.
        """
        status = res.status_code
        if status == EXPIRED_TOKEN_CODE:
            if "application/json" in res.headers["Content-Type"]:
                data = res.json()
                if "Invalid JWT token" in data["description"]:
                    return True
        return False
