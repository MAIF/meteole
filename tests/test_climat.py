import unittest
from unittest.mock import MagicMock
from datetime import datetime

from meteole.clients import MeteoFranceClient
from meteole.climat import (
    WeatherObservation,
    _format_departement,
    _distance_from_coords,
    sort_stations_by_distance,
)


class ConcreteObservation(WeatherObservation):
    MODEL_NAME = "TestModel"
    BASE_ENTRY_POINT = "https://api.example.com/test"
    MODEL_TYPE = "Observation"
    DEFAULT_FREQUENCY = "hourly"
    CLIENT_CLASS = MeteoFranceClient

    def _validate_parameters(self):
        pass


def make_obs(frequency="hourly"):
    client = MagicMock()
    obs = ConcreteObservation(client=client, frequency=frequency)
    return obs, client


class TestFormatDepartement(unittest.TestCase):
    def test_string_one_char_gets_padded(self):
        self.assertEqual(_format_departement("1"), "01")
        self.assertEqual(_format_departement("9"), "09")

    def test_overseas_departements(self):
        self.assertEqual(_format_departement("971"), "971")


class TestDistanceFromCoords(unittest.TestCase):
    def test_paris_to_lyon_approx(self):
        dist = _distance_from_coords(48.8566, 2.3522, 45.7640, 4.8357)
        self.assertGreater(dist, 380)
        self.assertLess(dist, 420)


class TestSortStationsByDistance(unittest.TestCase):
    def test_closest_first(self):
        ref_lat, ref_lon = 48.8566, 2.3522  # Paris
        stations = [
            {"name": "Lyon", "lat": 45.764, "lon": 4.835},
            {"name": "Versailles", "lat": 48.804, "lon": 2.130},
            {"name": "Marseille", "lat": 43.296, "lon": 5.381},
        ]
        sorted_s = sort_stations_by_distance(ref_lat, ref_lon, stations)
        self.assertEqual(sorted_s[0]["name"], "Versailles")


class TestFormatDatetime(unittest.TestCase):
    def test_hourly_strips_minutes(self):
        obs, _ = make_obs("hourly")
        dt = datetime(2024, 6, 15, 14, 37, 22)
        self.assertEqual(obs._format_datetime(dt), "2024-06-15T14:00:00Z")


class TestFetchStations(unittest.TestCase):
    def test_calls_correct_url_hourly(self):
        obs, client = make_obs("hourly")
        client.get.return_value.json.return_value = []
        obs._fetch_stations("75")
        url_called = client.get.call_args[0][0]
        self.assertIn("horaire", url_called)
        self.assertIn("liste-stations", url_called)


class TestFetchStationInfo(unittest.TestCase):
    def test_returns_dict(self):
        obs, client = make_obs()
        client.get.return_value.json.return_value = [{"id": 75056001, "name": "Station Test", "lat": 48.0, "lon": 2.0}]
        result = obs._fetch_station_info("75056001")
        self.assertIsInstance(result, dict)


class TestGetStationInfoCache(unittest.TestCase):
    def test_caches_result(self):
        obs, client = make_obs()
        client.get.return_value.json.return_value = [{"id": 75056001, "name": "T"}]
        obs.get_station_info("75056001")
        obs.get_station_info("75056001")
        self.assertEqual(client.get.call_count, 1)


class TestGetStations(unittest.TestCase):
    def test_sorted_by_distance_when_lat_lon_given(self):
        obs, _ = make_obs()
        obs._stations["75"] = [
            {"id": "far", "lat": 50.0, "lon": 5.0, "posteOuvert": True},
            {"id": "near", "lat": 48.86, "lon": 2.35, "posteOuvert": True},
        ]
        result = obs.get_stations("75", lat=48.8566, lon=2.3522, add_neighbours=False)
        self.assertEqual(result[0]["id"], "near")
