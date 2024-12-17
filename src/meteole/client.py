"""Core module for the MeteoFrance client package."""

import logging
import tempfile
import time
from pathlib import Path

import requests

from meteole.const import (
    EXPIRED_TOKEN_CODE,
    FORBIDDEN_CODE,
    MISSING_DATA_CODE,
    PARAMETER_ERROR_CODE,
    SPECIFIC_ERROR,
    SUCCESS_CODES,
)
from meteole.errors import GenericMeteofranceApiError, MissingDataError

logger = logging.getLogger(__name__)


class MeteoFranceClient:
    """
    A client for interacting with the Meteo France API.

    This class handles the connection setup and token refreshment required for
    authenticating and making requests to the Meteo France API.

    Attributes:
        api_key (str | None): The API key for accessing the Meteo France API.
        token (str | None): The authentication token for accessing the API.
        application_id (str | None): The application ID used for identification.
        verify (Path | None): The path to a file or directory of trusted CA certificates for SSL verification.
    """

    def __init__(
        self,
        api_key: str | None = None,
        token: str | None = None,
        application_id: str | None = None,
        verify: Path | None = None,
    ):
        """
        Initializes the MeteoFranceClient object.

        Args:
            api_key (str | None): The API key for accessing the Meteo France API.
            token (str | None): The authentication token for accessing the API.
            application_id (str | None): The application ID used for identification.
            verify (Path | None): The path to a file or directory of trusted CA certificates for SSL verification.
        """
        self.api_key = api_key
        self.token = token
        self.application_id = application_id
        self.verify = verify

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

    def get_token(self) -> str | None:
        """request a token from the meteo-France API.

        The token lasts 1 hour, and is used to authenticate the user.
        If a new token is requested before the previous one expires, the previous one is invalidated.
        A local cache is used to avoid requesting a new token at each run of the script.
        """
        # cache the token for 1 hour
        TOKEN_DURATION_S: int = 3600
        local_tmp_cache: str = tempfile.TemporaryDirectory().name
        cache_filename: Path = Path(local_tmp_cache) / "token.txt"
        cache_time_filename: Path = Path(local_tmp_cache) / "token_time.txt"

        # try to read  from cache
        if cache_filename.exists() and cache_time_filename.exists():
            logger.debug("reading token from cache")
            with open(cache_time_filename) as f:
                cache_time: float = float(f.read())
            if cache_time >= (time.time() - TOKEN_DURATION_S):
                with open(cache_filename) as f:
                    token: str = f.read()
                return token

        token_entrypoint: str = "https://portail-api.meteofrance.fr/token"
        params: dict[str, str] = {"grant_type": "client_credentials"}
        header: dict[str, str] = {"Authorization": "Basic " + str(self.application_id)}
        res: requests.Response = requests.post(
            token_entrypoint,
            params=params,
            headers=header,
            timeout=(30, 3600),
            verify=str(self.verify) if self.verify else None,
        )
        self.token = res.json()["access_token"]

        # save token to file
        Path(local_tmp_cache).mkdir(parents=True, exist_ok=True)
        with open(cache_filename, "w") as f:
            f.write(str(self.token))
        with open(cache_time_filename, "w") as f:
            f.write(str(time.time()))
        return self.token

    def _get_request(self, url, params=None, max_retries=5):
        """
        Makes a GET request to the API with optional retries.

        Args:
            url (str): The URL to send the GET request to.
            params (dict, optional): The query parameters to include in the request. Defaults to None.
            max_retries (int, optional): The maximum number of retry attempts in case of failure. Defaults to 5.

        Returns:
            requests.Response: The response returned by the API.

        """
        logger.debug(f"GET {url}")
        attempt = 0
        while attempt < max_retries:
            res = self.session.get(url, params=params, verify=self.verify)

            if self._token_expired(res):
                logger.info("token expired, requesting a new one")
                self.get_token()
                self.connect()
                res = self.session.get(url, params=params, verify=self.verify)
                return res

            error_code = res.status_code
            if error_code in SUCCESS_CODES:
                logger.debug("request successful")
                return res
            if error_code == FORBIDDEN_CODE:
                raise GenericMeteofranceApiError(res.text)
            if error_code == PARAMETER_ERROR_CODE:
                logger.error("parameter error")
                raise GenericMeteofranceApiError(res.text)
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
