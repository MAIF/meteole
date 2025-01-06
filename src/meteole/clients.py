"""API client classes"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

import requests
from requests import Response, Session

from meteole.errors import GenericMeteofranceApiError, MissingDataError

logger = logging.getLogger(__name__)


class HttpStatus(int, Enum):
    """Http status codes"""

    OK: int = 200
    BAD_REQUEST: int = 400
    UNAUTHORIZED: int = 401
    FORBIDDEN: int = 403
    NOT_FOUND: int = 404
    TOO_MANY_REQUESTS: int = 429
    INTERNAL_ERROR: int = 500
    BAD_GATEWAY: int = 502
    UNAVAILABLE: int = 503
    GATEWAY_TIMEOUT: int = 504


class BaseClient(ABC):
    """TODO"""

    @abstractmethod
    def get(self, path: str, *, params: dict[str, Any] | None = None, max_retries: int = 5) -> Response:
        """TODO"""
        raise NotImplementedError


class MeteoFranceClient(BaseClient):
    """A client for interacting with the Meteo France API.

    This class handles the connection setup and token refreshment required for
    authenticating and making requests to the Meteo France API.

    Attributes:
        api_key (str | None): The API key for accessing the Meteo France API.
        token (str | None): The authentication token for accessing the API.
        application_id (str | None): The application ID used for identification.
        verify (Path | None): The path to a file or directory of trusted CA certificates for SSL verification.
    """

    # Class constants
    API_BASE_URL: str = "https://public-api.meteofrance.fr/public/"
    TOKEN_URL: str = "https://portail-api.meteofrance.fr/token"
    GET_TOKEN_TIMEOUT_SEC: int = 10
    INVALID_JWT_ERROR_CODE: str = "900901"
    RETRY_DELAY_SEC: int = 5

    def __init__(
        self,
        *,
        token: str | None = None,
        api_key: str | None = None,
        application_id: str | None = None,
        certs_path: Path | None = None,
    ) -> None:
        """
        Initializes the MeteoFranceClient object.

        Args:
            api_key (str | None): The API key for accessing the Meteo France API.
            token (str | None): The authentication token for accessing the API.
            application_id (str | None): The application ID used for identification.
            verify (Path | None): The path to a file or directory of trusted CA certificates for SSL verification.
        """
        self._token = token
        self._api_key = api_key
        self._application_id = application_id
        self._verify: str | None = str(certs_path) if certs_path is not None else None

        self._session = Session()

        self._token_expired: bool = False

        # Initialize the requests session object
        self._connect()

    def get(self, path: str, *, params: dict[str, Any] | None = None, max_retries: int = 5) -> Response:
        """
        Makes a GET request to the API with optional retries.

        Args:
            url (str): The URL to send the GET request to.
            params (dict, optional): The query parameters to include in the request. Defaults to None.
            max_retries (int, optional): The maximum number of retry attempts in case of failure. Defaults to 5.

        Returns:
            requests.Response: The response returned by the API.

        """
        url: str = self.API_BASE_URL + path
        attempt: int = 0
        logger.debug(f"GET {url}")

        while attempt < max_retries:
            # HTTP GET request
            resp: Response = self._session.get(url, params=params, verify=self._verify)

            if resp.status_code == HttpStatus.OK:
                logger.debug("Successful request")
                return resp

            elif self._is_token_expired(resp):
                logger.info("Token expired, requesting a new one")

                # Refresh the cached token
                self._token = self._get_token()

                # Reconnect with the new token
                self._connect()

            elif resp.status_code == HttpStatus.FORBIDDEN:
                logger.error("Access forbidden")
                raise GenericMeteofranceApiError(resp.text)

            elif resp.status_code == HttpStatus.BAD_REQUEST:
                logger.error("Parameter error")
                raise GenericMeteofranceApiError(resp.text)

            elif resp.status_code == HttpStatus.NOT_FOUND:
                logger.error("Missing data")
                raise MissingDataError(resp.text)

            elif (
                resp.status_code == HttpStatus.BAD_GATEWAY
                or resp.status_code == HttpStatus.UNAVAILABLE
                or resp.status_code == HttpStatus.GATEWAY_TIMEOUT
            ):
                logger.error("Service not available")
                time.sleep(self.RETRY_DELAY_SEC)
                attempt += 1
                logger.info(f"Retrying... Attempt {attempt} of {max_retries}")
                continue

        raise GenericMeteofranceApiError(f"Failed to get a successful response from API after {attempt} retries")

    def _connect(self):
        """Connect to the MeteoFrance API.

        If the API key is provided, it is used to authenticate the user.
        If the token is provided, it is used to authenticate the user.
        If the application ID is provided, a token is requested from the API.
        """
        if self._api_key is None and self._token is None:
            if self._application_id is None:
                raise ValueError("api_key or token or application_id must be provided")

            # Connection with application_id
            self._token = self._get_token()

        if self._api_key is not None:
            logger.debug("using api key")

            # Connection with api_key
            self._session.headers.update({"apikey": self._api_key})

        else:
            logger.debug("using token")

            # Connection with token
            self._session.headers.update({"Authorization": f"Bearer {self._token}"})

    def _get_token(self) -> str:
        """request a token from the meteo-France API.

        The token lasts 1 hour, and is used to authenticate the user.
        If a new token is requested before the previous one expires, the previous one is invalidated.
        A local cache is used to avoid requesting a new token at each run of the script.
        """
        if self._token_expired is False and self._token is not None:
            # Use cached token
            token: str = self._token

        elif self._token_expired is True and self._application_id is None:
            # Can do nothing
            raise ValueError("The 'application_id' is unknown, can't get a new token")

        else:
            # Retrieve a new token

            # Seems useless (TODO remove if it's True):
            # params: dict[str, str] = {"grant_type": "client_credentials"}
            headers: dict[str, str] = {"Authorization": "Basic " + str(self._application_id)}

            resp: Response = requests.post(
                self.TOKEN_URL,
                # params=params,
                headers=headers,
                timeout=self.GET_TOKEN_TIMEOUT_SEC,
                verify=self._verify,
            )
            token = resp.json()["access_token"]

        return token

    def _is_token_expired(self, response: Response) -> bool:
        """Check if the token is expired.

        Returns
        -------
        bool
            True if the token is expired, False otherwise.
        """
        result: bool = False

        if response.status_code == HttpStatus.UNAUTHORIZED and "application/json" in response.headers["Content-Type"]:
            error: str = response.json()["code"]

            if error == self.INVALID_JWT_ERROR_CODE:
                result = True
                self._token_expired = True

        return result