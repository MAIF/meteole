"""
in _fetch_capabilities, there is some error catching and logging going one. But not on the other fetch_...
methods. I did not implement it here, perhaps it could be added to the client class so that it is common to all
requests.
On the same topic, if an error arrises in client.get, it is reraised with another more generic error, and
(as far as I understand) the type of error is lost. It would be useful here to catch some errors to output more
useful messages

From the doc:
erreur 404 "Not Found" lors de la recherche de stations => le département n'existe pas
erreur 400 "Bad Request" lors de la recherche de métadonnées d'une station ou du passage d'une commande => la station n'existe pas
erreur 400 "Bad Request" lors de la commande de données 6 minutes => la date de début est non conforme  :
Pour les données 6 minutes, la règle est la suivante : les minutes doivent être un multiple de 6 (00, 06, 12, 18, 24, 30, 36, 42, 48, 54)
erreur 400 "Bad Request" lors de la commande de données => la date de fin est dans le futur
bad request with response body : la période demandée ne doit pas dépasser 1 an
erreur 500 "Error: Internal Server Error" et message "production en échec (la commande contient une plage d'absence de
données)" lors de la récupération d'une commande => la période recherchée est sur une période d'inactivité de la station

"""

from __future__ import annotations

import datetime
import logging
import time
from abc import ABC, abstractmethod
from importlib.util import find_spec
from io import StringIO
from math import acos, cos, radians, sin
from typing import Any

import pandas as pd

from meteole.clients import BaseClient

if find_spec("cfgrib") is None:
    raise ImportError(
        "The 'cfgrib' module is required to read Arome and Arpege GRIB files. Please install it using:\n\n"
        "  conda install -c conda-forge cfgrib\n\n"
    )
logger = logging.getLogger(__name__)

NEIGHBOURS = {
    "01": ("38", "39", "69", "71", "73", "74"),
    "02": ("08", "51", "59", "60", "77", "80"),
    "2A": ("2B",),
    "2B": ("2A",),
    "03": ("18", "23", "42", "58", "63", "71"),
    "04": ("05", "06", "13", "83", "84", "26"),
    "05": ("04", "26", "38", "73"),
    "06": ("04", "83"),
    "07": ("26", "30", "43", "48", "84"),
    "08": ("02", "51", "55"),
    "09": ("11", "31", "66"),
    "10": ("21", "51", "52", "77", "89"),
    "11": ("09", "31", "34", "66", "81"),
    "12": ("15", "30", "34", "46", "48", "81", "82"),
    "13": ("04", "30", "83", "84"),
    "14": ("27", "50", "61"),
    "15": ("12", "19", "43", "46", "48", "63"),
    "16": ("17", "24", "79", "86", "87"),
    "17": ("16", "33", "79", "85"),
    "18": ("03", "36", "41", "45", "58"),
    "19": ("15", "23", "24", "46", "63", "87"),
    "21": ("10", "52", "58", "71", "89"),
    "22": ("29", "35", "56"),
    "23": ("03", "19", "36", "63", "87"),
    "24": ("16", "19", "33", "46", "47", "87"),
    "25": ("39", "70", "90"),
    "26": ("04", "05", "07", "38", "84"),
    "27": ("14", "28", "60", "76", "78", "95"),
    "28": ("27", "41", "45", "61", "72", "78", "91"),
    "29": ("22", "56"),
    "30": ("07", "12", "13", "34", "48", "84"),
    "31": ("09", "11", "32", "65", "81", "82"),
    "32": ("31", "40", "47", "64", "65", "82"),
    "33": ("17", "24", "40", "47"),
    "34": ("11", "12", "30", "81"),
    "35": ("22", "44", "49", "50", "53", "56"),
    "36": ("18", "23", "37", "41", "86", "87"),
    "37": ("36", "41", "49", "72", "86"),
    "38": ("01", "05", "26", "73", "74"),
    "39": ("01", "25", "71"),
    "40": ("32", "33", "47", "64"),
    "41": ("18", "28", "36", "37", "45", "72"),
    "42": ("03", "43", "63", "69", "71"),
    "43": ("07", "15", "42", "48", "63"),
    "44": ("35", "49", "56", "85"),
    "45": ("18", "28", "41", "77", "89", "91"),
    "46": ("12", "15", "19", "24", "47", "82"),
    "47": ("24", "32", "33", "40", "46", "82"),
    "48": ("07", "12", "15", "30", "43"),
    "49": ("35", "37", "44", "53", "72", "79", "85"),
    "50": ("14", "35", "53", "61"),
    "51": ("02", "08", "10", "52", "55", "77"),
    "52": ("10", "21", "51", "55", "70", "88"),
    "53": ("35", "49", "50", "61", "72"),
    "54": ("55", "57", "88"),
    "55": ("08", "51", "52", "54", "88"),
    "56": ("22", "29", "35", "44"),
    "57": ("54", "67", "88"),
    "58": ("03", "18", "21", "71", "89"),
    "59": ("02", "62", "80"),
    "60": ("02", "27", "76", "77", "80", "95"),
    "61": ("14", "28", "50", "53", "72"),
    "62": ("59", "80"),
    "63": ("03", "15", "19", "23", "42", "43"),
    "64": ("32", "40", "65"),
    "65": ("31", "32", "64"),
    "66": ("09", "11"),
    "67": ("57", "68", "88"),
    "68": ("67", "88", "90"),
    "69": ("01", "42", "71"),
    "70": ("25", "52", "88", "90"),
    "71": ("01", "03", "21", "39", "42", "58", "69"),
    "72": ("28", "37", "41", "49", "53", "61"),
    "73": ("01", "05", "38", "74"),
    "74": ("01", "38", "73"),
    "75": ("92", "93", "94"),
    "76": ("27", "60", "80"),
    "77": ("02", "10", "45", "51", "60", "89", "91", "93", "94"),
    "78": ("27", "28", "91", "92", "95"),
    "79": ("16", "17", "49", "85", "86"),
    "80": ("02", "59", "60", "62", "76"),
    "81": ("11", "12", "31", "34", "82"),
    "82": ("12", "31", "32", "46", "47", "81"),
    "83": ("04", "06", "13", "84"),
    "84": ("04", "07", "13", "26", "30", "83"),
    "85": ("17", "44", "49", "79"),
    "86": ("16", "36", "37", "79", "87"),
    "87": ("16", "19", "23", "24", "36", "86"),
    "88": ("52", "54", "55", "57", "67", "68", "70"),
    "89": ("10", "21", "45", "58", "77"),
    "90": ("25", "68", "70"),
    "91": ("28", "45", "77", "78", "92", "94"),
    "92": ("75", "78", "91", "93", "94"),
    "93": ("75", "77", "92", "94", "95"),
    "94": ("75", "77", "91", "92", "93"),
    "95": ("27", "60", "78", "93"),
    "99": tuple(),
    "971": tuple(),
    "972": tuple(),
    "973": tuple(),
    "974": tuple(),
    "975": tuple(),
    "984": tuple(),
    "985": tuple(),
    "986": tuple(),
    "987": tuple(),
    "988": tuple(),
}


def _format_departement(departement: int | str) -> str:
    """Formats a departement given as an int or a str into the proper two-character code

    ex: "01" -> "01", 1 -> "01", "1" -> "01", "unknown" -> ValueError
    """
    if isinstance(departement, float):
        raise ValueError("Invalid type (float) for departement, give it as str or int")
    if isinstance(departement, str) and len(departement) == 1:
        departement = "0" + departement
    if isinstance(departement, int):
        departement = f"{departement:02}"
    if departement not in NEIGHBOURS:
        raise ValueError(f"Invalid departement {departement}")
    return departement


def _distance_from_coords(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes the distance between two coordinates

    Args:
        lat1, lon1 (float): lat, lon of first point
        lat2, lon2 (float): lat, lon of second point

    Returns:
        float: distance (in km) between points.
    """

    lat1, lon1 = radians(lat1), radians(lon1)
    lat2, lon2 = radians(lat2), radians(lon2)
    return 6371.01 * acos(sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lon1 - lon2))


def sort_stations_by_distance(lat: float, lon: float, stations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sorts a list of stations by distance to a given point (lat, long)
    Returns a copy of the list, sorted
    """

    def _distance_to_point(station: dict[str, Any]) -> float:
        return _distance_from_coords(lat, lon, station["lat"], station["lon"])

    return sorted(stations, key=_distance_to_point)


class WeatherObservation(ABC):
    """(Abstract)
    Base class for weather observation models.

    Attributes:
        frequency: frequency of the observation ('6m','hourly', 'daily', 'decade', 'monthly')
    """

    # Class constants
    # Global
    API_VERSION: str = "v1"
    FREQUENCY_TO_ENDPOINT: dict[str, str] = {
        "6m": "infrahoraire-6m",
        "hourly": "horaire",
        "daily": "quotidienne",
        "decade": "decadaire",
        "monthly": "mensuelle",
    }
    # Model
    MODEL_NAME: str = "Defined in subclass"
    BASE_ENTRY_POINT: str = "Defined in subclass"
    MODEL_TYPE: str = "Observation"
    DEFAULT_FREQUENCY: str = "hourly"
    CLIENT_CLASS: type[BaseClient]

    def __init__(
        self,
        client: BaseClient | None = None,
        *,
        frequency: str = DEFAULT_FREQUENCY,
        **kwargs: Any,
    ):
        """Initialize attributes.

        Args:
            frequency: the observation frequency: '6m','hourly', 'daily', 'decade', 'monthly'
            api_key: The API key for authentication. Defaults to None.
            token: The API token for authentication. Defaults to None.
            application_id: The Application ID for authentication. Defaults to None.
        """

        self.frequency = frequency
        self._validate_parameters()

        self._entry_point = f"{self.BASE_ENTRY_POINT}/{self.API_VERSION}"

        # Stations are fetched and listed by departement number
        self._stations: dict[str, Any] = {}

        # Stations info are fetched and stored by station_id
        self._stations_info: dict[str, Any] = {}

        if client is not None:
            self._client = client
        else:
            # Try to instantiate it (can be user friendly)
            self._client = self.CLIENT_CLASS(**kwargs)

    @abstractmethod
    def _validate_parameters(self) -> None:
        pass

    def get_stations(
        self,
        departement: int | str,
        lat: float | None = None,
        lon: float | None = None,
        add_neighbours: bool = True,
        open_only: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Returns a list of station for a given departement.

        Typically, one needs the closest or the N closest stations to a given point. When lat, lon parameters are
        specified, the results are sorted by distance to that point, with the closest station first in the list.

        In the same vein, setting add_neighbours to True adds stations from neighbouring departements. This is useful
        when looking for stations close to the border of a departement.

        Args:
            departement: departement number (int or str)
            add_neighbours: bool (default True), whether to add stations from bordering departements
            open_only: bool (default True), whether to return only stations currently open

            if lat, lon are given, the stations are sorted by distance to this point
        """
        departement = _format_departement(departement)

        if departement not in self._stations:
            self._stations[departement] = self._fetch_stations(departement)

        out = self._stations[departement]
        if open_only:
            out = [station for station in out if station.get("posteOuvert", False)]

        if add_neighbours:
            for neighbour in NEIGHBOURS[departement]:
                out.extend(self.get_stations(neighbour, add_neighbours=False, open_only=open_only))

        if lat and lon:
            out = sort_stations_by_distance(lat, lon, out)

        return out

    def _fetch_stations(self, departement: int | str) -> list[dict[str, Any]]:
        """Fetch all stations from a departement

        Args:
            departement: departement number (int or str)

        Returns:
            list of stations. each station is a dict.
        """
        url = f"{self._entry_point}/liste-stations/"
        if self.frequency in ("6m", "hourly"):
            url += self.FREQUENCY_TO_ENDPOINT[self.frequency]
        else:
            url += "quotidienne"

        params = {"id-departement": _format_departement(departement)}

        response = self._client.get(url, params=params)
        return response.json()

    def get_station_info(self, station_id: str) -> dict[str, Any]:
        """Returns the information for a particular station as a dict (raw output from the API)
        Caches the information for future use
        """
        if station_id not in self._stations_info:
            self._stations_info[station_id] = self._fetch_station_info(station_id)
        return self._stations_info[station_id]

    def _fetch_station_info(self, station_id: str) -> dict[str, Any]:
        """
        Gets the information for a particular station
        """
        url = f"{self._entry_point}/information-station"
        params = {"id-station": station_id}

        response = self._client.get(url, params=params)

        response = response.json()[0]  # returns a list with one element

        print(type(response["id"]))

        # There seem to be a bug in the API where the ID of the station has been transformed into an integer, which
        # suppresses leading zeros. We fix it here : convert to str and add leading zeros if necessary.
        # We checked that it is not due to the conversion in response.json() : it is already truncated in response.text
        if len(id_str := str(response["id"])) < 8:
            id_str = "0" * (8 - len(id_str)) + id_str
        response["id"] = id_str

        return response

    def fetch_data(
        self, station_id: str, start: datetime.datetime | str, end: datetime.datetime | str, wait_for_file: int = 5
    ) -> pd.DataFrame:
        """Get observations for a station and a given time period. Fetching the data happens in two steps: first, an
            order is placed, it is processed by the server, and after a certain waiting time, the file is retrieved.

            Args:
            station_id (str): the station id
            start and end (str or datetime): time period. Can be given as a datetime or a str. As a str,
                must be of the form : AAAA-MM-JJThh:mm:00Z, with minutes and hours depending on the frequency.
                For hourly data, minutes must be 00. For daily data, hours and minutes must be 00:00. For 6-minute
                data, minutes must be a multiple of 6 (00, 06, 12, 18, 24, 30, 36, 42, 48, 54).
            wait_for_file (int): number of seconds to wait before retrieving the file after ordering it.

        Returns:
            pd.DataFrame: The forecast for the specified time.
        """

        if isinstance(start, datetime.datetime):
            start = self._format_datetime(start)
        if isinstance(end, datetime.datetime):
            end = self._format_datetime(end)

        # order data and retrieve order ID
        self._order_id = self._order_data(station_id, start, end)

        # file is typically ready after a few seconds
        time.sleep(wait_for_file)
        file_content = self._retrieve_file(order_id=self._order_id)
        return pd.read_csv(StringIO(file_content), delimiter=";", decimal=",")

    def _order_data(self, station_id: str, start: str, end: str) -> str:
        """
        Orders data for a given station and period
        Returns the order ID
        """
        url = f"{self._entry_point}/commande-station/{self.FREQUENCY_TO_ENDPOINT[self.frequency]}"

        params = {"id-station": station_id, "date-deb-periode": start, "date-fin-periode": end}

        response = self._client.get(url, params=params).json()
        return response["elaboreProduitAvecDemandeResponse"]["return"]

    def _retrieve_file(self, order_id: str) -> str:
        """Retrieve the file corresponsing to order_id
        HTTPERROR 204 indicates that the file is not yet ready

        Returns .csv file content as a string
        """
        url = f"{self._entry_point}/commande/fichier"
        params = {"id-cmde": order_id}
        response = self._client.get(url, params=params)
        return response.text

    def _format_datetime(self, dt: datetime.datetime) -> str:
        """Checks and formats the start and end dates for ordering data
        Trims the datetimes to the appropriate precision
        """
        # Trim to proper precision
        dt = dt.replace(second=0, microsecond=0)

        if self.frequency == "6m":
            # For 6-minute data, minutes must be a multiple of 6 (00, 06, 12, 18, 24, 30, 36, 42, 48, 54)
            dt = dt.replace(minute=int(dt.minute / 6) * 6)
        elif self.frequency == "hourly":
            dt = dt.replace(minute=0)
        elif self.frequency in ("daily", "decade", "monthly"):
            dt = dt.replace(hour=0, minute=0)

        return dt.isoformat().removesuffix("+00:00") + "Z"
