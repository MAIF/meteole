from unittest.mock import MagicMock, patch

import pytest

from meteole.client import MeteoFranceClient


def test_init_with_api_key():
    api = MeteoFranceClient(api_key="dummy_api_key")
    assert api.api_key == "dummy_api_key"
    assert api.token is None
    assert api.application_id is None


def test_init_with_token():
    api = MeteoFranceClient(token="dummy_token")
    assert api.api_key is None
    assert api.token == "dummy_token"
    assert api.application_id is None


@patch("meteole.client.MeteoFranceClient.connect")
def test_init_with_application_id(mock_connect):
    api = MeteoFranceClient(application_id="dummy_app_id")
    assert api.application_id == "dummy_app_id"
    assert api.api_key is None


def test_connect_no_credentials():
    with pytest.raises(ValueError):
        MeteoFranceClient()


@patch("requests.post")
def test_get_token(mock_post):
    mock_post.return_value.json.return_value = {"access_token": "dummy_token"}

    api = MeteoFranceClient(application_id="dummy_app_id")
    token = api.get_token()

    assert token == "dummy_token"
    assert api.token == "dummy_token"


@patch("requests.Session.get")
@patch.object(MeteoFranceClient, "get_token")
def test_get_request_success(mock_get_token, mock_get):
    api = MeteoFranceClient(api_key="dummy_api_key")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "some data"}
    mock_get.return_value = mock_response

    response = api._get_request("https://dummyurl.com")
    assert response.status_code == 200
    assert response.json() == {"data": "some data"}


@patch("requests.Session.get")
@patch.object(MeteoFranceClient, "get_token")
def test_get_request_token_expired(mock_get_token, mock_get):
    api = MeteoFranceClient(api_key="dummy_api_key")

    expired_response = MagicMock()
    expired_response.status_code = 401
    expired_response.headers = {"Content-Type": "application/json"}
    expired_response.json.return_value = {"description": "Invalid JWT token"}

    valid_response = MagicMock()
    valid_response.status_code = 200
    valid_response.json.return_value = {"data": "some data"}

    mock_get.side_effect = [expired_response, valid_response, valid_response]

    response = api._get_request("https://dummyurl.com")
    assert response.status_code == 200
    assert response.json() == {"data": "some data"}

    response = api._get_request("https://dummyurl.com")
    assert response.status_code == 200
    assert response.json() == {"data": "some data"}


def test_token_expired():
    api = MeteoFranceClient(api_key="dummy_api_key")
    expired_response = MagicMock()
    expired_response.status_code = 401
    expired_response.headers = {"Content-Type": "application/json"}
    expired_response.json = lambda: {"description": "Invalid JWT token"}

    assert api._token_expired(expired_response) == True


def test_token_not_expired():
    api = MeteoFranceClient(api_key="dummy_api_key")
    valid_response = MagicMock()
    valid_response.status_code = 200
    valid_response.headers = {"Content-Type": "application/json"}
    valid_response.text = lambda: {"description": "Valid JWT token"}

    assert api._token_expired(valid_response) == False


@patch("requests.Session.get")
@patch.object(MeteoFranceClient, "get_token")
def test_get_request_specific_error(mock_get_token, mock_get):
    api = MeteoFranceClient(api_key="dummy_api_key")

    error_response = MagicMock()
    error_response.status_code = 502
    error_response.json.return_value = {"error": "Bad Gateway"}

    valid_response = MagicMock()
    valid_response.status_code = 200
    valid_response.json.return_value = {"data": "some data"}

    mock_get.side_effect = [error_response, valid_response]

    response = api._get_request("https://dummyurl.com")
    assert response.status_code == 200
    assert response.json() == {"data": "some data"}
    assert mock_get.call_count == 2
