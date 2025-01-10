import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from meteole._arpege import ArpegeForecast
from meteole._arome import AromeForecast
from meteole.clients import MeteoFranceClient


class TestAromeForecast(unittest.TestCase):
    def setUp(self):
        self.precision = 0.01
        self.territory = "FRANCE"
        self._api_key = "fake_api_key"
        self.token = "fake_token"
        self.application_id = "fake_app_id"
        self.certs_path = "a/path/"
        self.client = MeteoFranceClient(
            api_key=self._api_key, token=self.token, application_id=self.application_id, certs_path=self.certs_path
        )

    @patch("meteole._arome.AromeForecast.get_capabilities")
    def test_initialization(self, mock_get_capabilities):
        mock_get_capabilities.return_value = None

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )

        self.assertEqual(forecast.precision, self.precision)
        self.assertEqual(forecast.territory, self.territory)
        self.assertEqual(forecast._client._api_key, self._api_key)
        self.assertEqual(forecast._client._token, self.token)
        self.assertEqual(forecast._client._application_id, self.application_id)
        self.assertEqual(forecast._client._verify, self.certs_path)
        self.assertEqual(forecast.MODEL_NAME, "arome")
        self.assertEqual(len(forecast.INDICATORS), 19)
        # mock_get_capabilities.assert_called_once()

    def test_invalid_precision(self):
        with self.assertRaises(ValueError):
            AromeForecast(self.client, precision=0.1)

    def test_invalid_territory(self):
        with self.assertRaises(ValueError):
            AromeForecast(self.client, territory="INVALID")

    @patch("meteole.clients.MeteoFranceClient.get")
    def test_get_capabilities(self, mock_get_request):
        mock_response = MagicMock()
        mock_response.text = """
            <wcs:Capabilities>
                <wcs:Contents>
                    <wcs:CoverageSummary>
                        <wcs:CoverageId>GEOMETRIC_HEIGHT__GROUND_OR_WATER_SURFACE___2024-10-31T00.00.00Z</wcs:CoverageId>
                        <ows:CoverageTitle>Geometric height</ows:CoverageTitle>
                        <wcs:CoverageSubtype>ReferenceableGridCoverage</wcs:CoverageSubtype>
                    </wcs:CoverageSummary>
                    <wcs:CoverageSummary>
                        <wcs:CoverageId>SHORT_WAVE_RADIATION_FLUX__GROUND_OR_WATER_SURFACE___2024-11-01T18.00.00Z_P2D</wcs:CoverageId>
                        <ows:CoverageTitle>short-wave radiation flux</ows:CoverageTitle>
                        <wcs:CoverageSubtype>ReferenceableGridCoverage</wcs:CoverageSubtype>
                    </wcs:CoverageSummary>
                </wcs:Contents>
            </wcs:Capabilities>
        """
        mock_get_request.return_value = mock_response

        arome = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )
        # arome.get_capabilities() is made during init
        # this means arome.capabilities exists now

        self.assertEqual(
            list(arome.capabilities["id"]),
            [
                "GEOMETRIC_HEIGHT__GROUND_OR_WATER_SURFACE___2024-10-31T00.00.00Z",
                "SHORT_WAVE_RADIATION_FLUX__GROUND_OR_WATER_SURFACE___2024-11-01T18.00.00Z_P2D",
            ],
        )

    @patch("meteole.clients.MeteoFranceClient.get")
    def test_get_coverage_id(self, mock_get_request):
        mock_response = MagicMock()
        mock_response.text = """
            <wcs:Capabilities>
                <wcs:Contents>
                    <wcs:CoverageSummary>
                        <wcs:CoverageId>GEOMETRIC_HEIGHT__GROUND_OR_WATER_SURFACE___2024-10-31T00.00.00Z</wcs:CoverageId>
                        <ows:CoverageTitle>Geometric height</ows:CoverageTitle>
                        <wcs:CoverageSubtype>ReferenceableGridCoverage</wcs:CoverageSubtype>
                    </wcs:CoverageSummary>
                    <wcs:CoverageSummary>
                        <wcs:CoverageId>TOTAL_WATER_PRECIPITATION__GROUND_OR_WATER_SURFACE___2024-11-01T18.00.00Z_P2D</wcs:CoverageId>
                        <ows:CoverageTitle>short-wave radiation flux</ows:CoverageTitle>
                        <wcs:CoverageSubtype>ReferenceableGridCoverage</wcs:CoverageSubtype>
                    </wcs:CoverageSummary>
                </wcs:Contents>
            </wcs:Capabilities>
        """
        mock_get_request.return_value = mock_response

        arome = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )  # arome.capabilities is set up

        run = "2024-11-01T18.00.00Z"
        interval = "P2D"

        # test wrong indicator raises
        indicator = "wrong_indicator"

        with pytest.raises(ValueError):
            coverage_id = arome._get_coverage_id(indicator, run, interval)

        indicator = "TOTAL_WATER_PRECIPITATION__GROUND_OR_WATER_SURFACE"
        coverage_id = arome._get_coverage_id(indicator, run, interval)
        assert coverage_id == "TOTAL_WATER_PRECIPITATION__GROUND_OR_WATER_SURFACE___2024-11-01T18.00.00Z_P2D"

    @patch("meteole._arome.AromeForecast.get_capabilities")
    @patch("meteole.clients.MeteoFranceClient.get")
    def test_get_coverage_description(self, mock_get_request, mock_get_capabilities):
        mock_response = MagicMock()
        mock_response.text = """
            <wcs:CoverageDescriptions xmlns:wcs="http://www.opengis.net/wcs/2.0" xmlns:swe="http://www.opengis.net/swe/2.0" xmlns:gmlrgrid="http://www.opengis.net/gml/3.3/rgrid" xmlns:gmlcov="http://www.opengis.net/gmlcov/1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:gml="http://www.opengis.net/gml/3.2" xsi:schemaLocation="     http://www.opengis.net/wcs/2.0 http://schemas.opengis.net/wcs/2.0/wcsAll.xsd     http://www.opengis.net/gml/3.2 http://schemas.opengis.net/gml/3.2.1/gml.xsd     http://www.opengis.net/gmlcov/1.0 http://schemas.opengis.net/gmlcov/1.0/gmlcovAll.xsd     http://www.opengis.net/swe/2.0 http://schemas.opengis.net/sweCommon/2.0/swe.xsd     http://www.opengis.net/gml/3.3/rgrid http://schemas.opengis.net/gml/3.3/referenceableGrid.xsd">
            <wcs:CoverageDescription gml:id="U_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND___2024-06-20T09.00.00Z">
                <wcs:CoverageId>U_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND___2024-06-20T09.00.00Z</wcs:CoverageId>
                <wcs:ServiceParameters>
                <wcs:CoverageSubtype>ReferenceableGridCoverage</wcs:CoverageSubtype>
                <wcs:nativeFormat>application/wmo-grib</wcs:nativeFormat>
                </wcs:ServiceParameters>
            </wcs:CoverageDescription>
            </wcs:CoverageDescriptions>
        """
        mock_get_request.return_value = mock_response
        mock_get_capabilities.return_value = None

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )

        description = forecast._get_coverage_description("coverage_1")
        self.assertIn("wcs:CoverageDescriptions", description)

    @patch("meteole._arome.AromeForecast.get_capabilities")
    @patch("meteole._arome.AromeForecast._grib_bytes_to_df")
    @patch("meteole._arome.AromeForecast._get_coverage_file")
    def test_get_data_single_forecast(self, mock_get_coverage_file, mock_grib_bytes_to_df, mock_get_capabilities):
        mock_grib_bytes_to_df.return_value = pd.DataFrame({"data": [1, 2, 3]})

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )

        df = forecast._get_data_single_forecast(
            coverage_id="coverage_1",
            height=None,
            pressure=None,
            forecast_horizon=0,
            lat=(37.5, 55.4),
            long=(-12, 16),
        )

        self.assertTrue("data" in df.columns)

    @patch("meteole._arome.AromeForecast.get_capabilities")
    @patch("meteole._arome.AromeForecast._grib_bytes_to_df")
    @patch("meteole._arome.AromeForecast._get_coverage_file")
    def test_get_data_single_forecast_with_height(
        self, mock_get_coverage_file, mock_grib_bytes_to_df, mock_get_capabilities
    ):
        mock_get_coverage_file.return_value = ""
        mock_grib_bytes_to_df.return_value = pd.DataFrame({"data": [1, 2, 3], "heightAboveGround": ["2", "2", "2"]})

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )

        df = forecast._get_data_single_forecast(
            coverage_id="coverage_1",
            height=2,
            pressure=None,
            forecast_horizon=0,
            lat=(37.5, 55.4),
            long=(-12, 16),
        )

        self.assertTrue("data_2m" in df.columns)

    @patch("meteole._arome.AromeForecast.get_coverage_description")
    @patch("meteole._arome.AromeForecast.get_capabilities")
    @patch("meteole._arome.AromeForecast._get_data_single_forecast")
    def test_get_coverage(self, mock_get_data_single_forecast, mock_get_capabilities, mock_get_coverage_description):
        mock_get_data_single_forecast.return_value = pd.DataFrame(
            {
                "latitude": [1, 2, 3],
                "longitude": [4, 5, 6],
                "time": [7, 8, 9],
                "step": [10, 11, 12],
                "valid_time": [16, 17, 18],
                "data": [19, 20, 21],  # this column name varies depending on the coverage_id
            }
        )
        mock_get_coverage_description.return_value = {"heights": [2], "forecast_horizons": [0], "pressures": []}

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )

        forecast.get_coverage(
            coverage_id="toto",
            heights=[2],
            forecast_horizons=[0],
            lat=(37.5, 55.4),
            long=(-12, 16),
        )

        mock_get_data_single_forecast.assert_called_once_with(
            coverage_id="toto", height=2, pressure=None, forecast_horizon=0, lat=(37.5, 55.4), long=(-12, 16)
        )

    @patch("meteole._arome.AromeForecast.get_coverage_description")
    def test_get_forecast_horizons(self, mock_get_coverage_description):
        def side_effect(coverage_id):
            if coverage_id == "id1":
                return {"forecast_horizons": [0, 1, 2], "heights": [], "pressures": []}
            elif coverage_id == "id2":
                return {"forecast_horizons": [0, 2, 3], "heights": [], "pressures": []}

        mock_get_coverage_description.side_effect = side_effect

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )

        coverage_ids = ["id1", "id2"]
        expected_result = [[0, 1, 2], [0, 2, 3]]
        result = forecast._get_forecast_horizons(coverage_ids)
        self.assertEqual(result, expected_result)

    @patch("meteole._arome.AromeForecast._get_forecast_horizons")
    def test_find_common_forecast_horizons(self, mock_get_forecast_horizons):
        mock_get_forecast_horizons.return_value = [[0, 1, 2, 3], [2, 3, 4, 5], [1, 2, 3, 6]]

        list_coverage_id = ["id1", "id2", "id3"]
        expected_result = [2, 3]

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )
        result = forecast.find_common_forecast_horizons(list_coverage_id)
        self.assertEqual(result, expected_result)

    @patch("meteole._arome.AromeForecast._get_forecast_horizons")
    def test_validate_forecast_horizons_valid(self, mock_get_forecast_horizons):
        mock_get_forecast_horizons.return_value = [[0, 1, 2, 3], [2, 3, 4, 5]]

        coverage_ids = ["id1", "id2"]
        forecast_horizons = [2, 3]
        expected_result = []

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )
        result = forecast._validate_forecast_horizons(coverage_ids, forecast_horizons)
        self.assertEqual(result, expected_result)

    @patch("meteole._arome.AromeForecast._get_forecast_horizons")
    def test_validate_forecast_horizons_invalid(self, mock_get_forecast_horizons):
        mock_get_forecast_horizons.return_value = [[0, 1, 2, 3], [2, 3, 4, 5]]

        coverage_ids = ["id1", "id2"]
        forecast_horizons = [1, 2]
        expected_result = ["id2"]

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )
        result = forecast._validate_forecast_horizons(coverage_ids, forecast_horizons)
        self.assertEqual(result, expected_result)

    @patch("meteole._arome.AromeForecast._get_coverage_id")
    @patch("meteole._arome.AromeForecast.find_common_forecast_horizons")
    @patch("meteole._arome.AromeForecast._validate_forecast_horizons")
    @patch("meteole._arome.AromeForecast.get_coverage")
    def test_get_combined_coverage(
        self,
        mock_get_coverage,
        mock_validate_forecast_horizons,
        mock_find_common_forecast_horizons,
        mock_get_coverage_id,
    ):
        mock_get_coverage_id.side_effect = lambda indicator, run, interval: f"{indicator}_{run}_{interval}"
        mock_find_common_forecast_horizons.return_value = [0]
        mock_validate_forecast_horizons.return_value = []
        mock_get_coverage.side_effect = [
            pd.DataFrame(
                {
                    "latitude": [1, 2],
                    "longitude": [3, 4],
                    "run": ["2024-12-13T00.00.00Z", "2024-12-13T00.00.00Z"],
                    "forecast_horizon": [0, 0],
                    "data1": [10, 20],
                }
            ),
            pd.DataFrame(
                {
                    "latitude": [1, 2],
                    "longitude": [3, 4],
                    "run": ["2024-12-13T00.00.00Z", "2024-12-13T00.00.00Z"],
                    "forecast_horizon": [0, 0],
                    "data2": [30, 40],
                }
            ),
        ]

        indicator_names = [
            "GEOMETRIC_HEIGHT__GROUND_OR_WATER_SURFACE",
            "BRIGHTNESS_TEMPERATURE__GROUND_OR_WATER_SURFACE",
        ]
        runs = ["2024-12-13T00.00.00Z"]
        heights = [None, 2]
        pressures = [None, None]
        intervals = ["", "P1D"]
        lat = (37.5, 55.4)
        long = (-12, 16)
        forecast_horizons = [0]

        expected_result = pd.DataFrame(
            {
                "latitude": [1, 2],
                "longitude": [3, 4],
                "run": ["2024-12-13T00.00.00Z", "2024-12-13T00.00.00Z"],
                "forecast_horizon": [0, 0],
                "data1": [10, 20],
                "data2": [30, 40],
            }
        )

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )

        result = forecast.get_combined_coverage(
            indicator_names, runs, heights, pressures, intervals, lat, long, forecast_horizons
        )
        pd.testing.assert_frame_equal(result, expected_result)

    @patch("meteole._arome.AromeForecast._get_coverage_id")
    @patch("meteole._arome.AromeForecast.find_common_forecast_horizons")
    @patch("meteole._arome.AromeForecast._validate_forecast_horizons")
    @patch("meteole._arome.AromeForecast.get_coverage")
    def test_get_combined_coverage_invalid_forecast_horizons(
        self,
        mock_get_coverage,
        mock_validate_forecast_horizons,
        mock_find_common_forecast_horizons,
        mock_get_coverage_id,
    ):
        mock_get_coverage_id.side_effect = lambda indicator, run, interval: f"{indicator}_{run}_{interval}"
        mock_find_common_forecast_horizons.return_value = [0]
        mock_validate_forecast_horizons.return_value = [
            "GEOMETRIC_HEIGHT__GROUND_OR_WATER_SURFACE_2024-12-13T00.00.00Z"
        ]

        indicator_names = [
            "GEOMETRIC_HEIGHT__GROUND_OR_WATER_SURFACE",
            "BRIGHTNESS_TEMPERATURE__GROUND_OR_WATER_SURFACE",
        ]
        runs = ["2024-12-13T00.00.00Z"]
        heights = [None, 2]
        pressures = [None, None]
        intervals = ["", "P1D"]
        lat = (37.5, 55.4)
        long = (-12, 16)
        forecast_horizons = [0]

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )

        with self.assertRaises(ValueError) as context:
            forecast.get_combined_coverage(
                indicator_names, runs, heights, pressures, intervals, lat, long, forecast_horizons
            )
        self.assertIn("are not valid for these coverage_ids", str(context.exception))

    @patch("meteole._arome.AromeForecast._get_coverage_id")
    @patch("meteole._arome.AromeForecast.find_common_forecast_horizons")
    @patch("meteole._arome.AromeForecast._validate_forecast_horizons")
    @patch("meteole._arome.AromeForecast.get_coverage")
    def test_get_combined_coverage_multiple_runs(
        self,
        mock_get_coverage,
        mock_validate_forecast_horizons,
        mock_find_common_forecast_horizons,
        mock_get_coverage_id,
    ):
        # Mock return values
        mock_get_coverage_id.side_effect = lambda indicator, run, interval: f"{indicator}_{run}_{interval}"
        mock_find_common_forecast_horizons.return_value = [0]
        mock_validate_forecast_horizons.return_value = []
        mock_get_coverage.side_effect = [
            pd.DataFrame(
                {
                    "latitude": [1, 2],
                    "longitude": [3, 4],
                    "run": ["2024-12-13T00.00.00Z", "2024-12-13T00.00.00Z"],
                    "forecast_horizon": [0, 0],
                    "data1": [10, 20],
                }
            ),
            pd.DataFrame(
                {
                    "latitude": [1, 2],
                    "longitude": [3, 4],
                    "run": ["2024-12-13T00.00.00Z", "2024-12-13T00.00.00Z"],
                    "forecast_horizon": [0, 0],
                    "data2": [30, 40],
                }
            ),
            pd.DataFrame(
                {
                    "latitude": [1, 2],
                    "longitude": [3, 4],
                    "run": ["2024-12-14T00.00.00Z", "2024-12-14T00.00.00Z"],
                    "forecast_horizon": [0, 0],
                    "data1": [100, 200],
                }
            ),
            pd.DataFrame(
                {
                    "latitude": [1, 2],
                    "longitude": [3, 4],
                    "run": ["2024-12-14T00.00.00Z", "2024-12-14T00.00.00Z"],
                    "forecast_horizon": [0, 0],
                    "data2": [300, 400],
                }
            ),
        ]

        indicator_names = [
            "GEOMETRIC_HEIGHT__GROUND_OR_WATER_SURFACE",
            "BRIGHTNESS_TEMPERATURE__GROUND_OR_WATER_SURFACE",
        ]
        runs = ["2024-12-13T00.00.00Z", "2024-12-14T00.00.00Z"]
        heights = [None, 2]
        pressures = [None, None]
        intervals = ["", "P1D"]
        lat = (37.5, 55.4)
        long = (-12, 16)
        forecast_horizons = [0]

        expected_result = pd.DataFrame(
            {
                "latitude": [1, 2, 1, 2],
                "longitude": [3, 4, 3, 4],
                "run": ["2024-12-13T00.00.00Z", "2024-12-13T00.00.00Z", "2024-12-14T00.00.00Z", "2024-12-14T00.00.00Z"],
                "forecast_horizon": [0, 0, 0, 0],
                "data1": [10, 20, 100, 200],
                "data2": [30, 40, 300, 400],
            }
        )

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )

        result = forecast.get_combined_coverage(
            indicator_names, runs, heights, pressures, intervals, lat, long, forecast_horizons
        )
        pd.testing.assert_frame_equal(result, expected_result)

    @patch("meteole._arome.AromeForecast._get_coverage_id")
    @patch("meteole._arome.AromeForecast.find_common_forecast_horizons")
    @patch("meteole._arome.AromeForecast._validate_forecast_horizons")
    @patch("meteole._arome.AromeForecast.get_coverage")
    def test_get_combined_coverage_no_heights_or_pressures(
        self,
        mock_get_coverage,
        mock_validate_forecast_horizons,
        mock_find_common_forecast_horizons,
        mock_get_coverage_id,
    ):
        mock_get_coverage_id.side_effect = lambda indicator, run, interval: f"{indicator}_{run}_{interval}"
        mock_find_common_forecast_horizons.return_value = [0]
        mock_validate_forecast_horizons.return_value = []
        mock_get_coverage.side_effect = [
            pd.DataFrame(
                {
                    "latitude": [1, 2],
                    "longitude": [3, 4],
                    "run": ["2024-12-13T00.00.00Z", "2024-12-13T00.00.00Z"],
                    "forecast_horizon": [0, 0],
                    "data1": [10, 20],
                }
            ),
            pd.DataFrame(
                {
                    "latitude": [1, 2],
                    "longitude": [3, 4],
                    "run": ["2024-12-13T00.00.00Z", "2024-12-13T00.00.00Z"],
                    "forecast_horizon": [0, 0],
                    "data2": [30, 40],
                }
            ),
        ]

        indicator_names = [
            "GEOMETRIC_HEIGHT__GROUND_OR_WATER_SURFACE",
            "BRIGHTNESS_TEMPERATURE__GROUND_OR_WATER_SURFACE",
        ]
        runs = ["2024-12-13T00.00.00Z"]
        heights = None
        pressures = None
        intervals = ["", "P1D"]
        lat = (37.5, 55.4)
        long = (-12, 16)
        forecast_horizons = [0]

        expected_result = pd.DataFrame(
            {
                "latitude": [1, 2],
                "longitude": [3, 4],
                "run": ["2024-12-13T00.00.00Z", "2024-12-13T00.00.00Z"],
                "forecast_horizon": [0, 0],
                "data1": [10, 20],
                "data2": [30, 40],
            }
        )

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )

        result = forecast.get_combined_coverage(
            indicator_names, runs, heights, pressures, intervals, lat, long, forecast_horizons
        )
        pd.testing.assert_frame_equal(result, expected_result)

    @patch("meteole._arome.AromeForecast._get_coverage_id")
    @patch("meteole._arome.AromeForecast.find_common_forecast_horizons")
    @patch("meteole._arome.AromeForecast._validate_forecast_horizons")
    @patch("meteole._arome.AromeForecast.get_coverage")
    def test_get_combined_coverage_no_optional_params(
        self,
        mock_get_coverage,
        mock_validate_forecast_horizons,
        mock_find_common_forecast_horizons,
        mock_get_coverage_id,
    ):
        mock_get_coverage_id.side_effect = lambda indicator, run, interval: f"{indicator}_{run}_{interval}"
        mock_find_common_forecast_horizons.return_value = [0]
        mock_validate_forecast_horizons.return_value = []
        mock_get_coverage.side_effect = [
            pd.DataFrame(
                {
                    "latitude": [1, 2],
                    "longitude": [3, 4],
                    "run": ["2024-12-13T00.00.00Z", "2024-12-13T00.00.00Z"],
                    "forecast_horizon": [0, 0],
                    "data1": [10, 20],
                }
            ),
            pd.DataFrame(
                {
                    "latitude": [1, 2],
                    "longitude": [3, 4],
                    "run": ["2024-12-13T00.00.00Z", "2024-12-13T00.00.00Z"],
                    "forecast_horizon": [0, 0],
                    "data2": [30, 40],
                }
            ),
        ]

        indicator_names = [
            "GEOMETRIC_HEIGHT__GROUND_OR_WATER_SURFACE",
            "BRIGHTNESS_TEMPERATURE__GROUND_OR_WATER_SURFACE",
        ]
        runs = ["2024-12-13T00.00.00Z"]

        expected_result = pd.DataFrame(
            {
                "latitude": [1, 2],
                "longitude": [3, 4],
                "run": ["2024-12-13T00.00.00Z", "2024-12-13T00.00.00Z"],
                "forecast_horizon": [0, 0],
                "data1": [10, 20],
                "data2": [30, 40],
            }
        )

        forecast = AromeForecast(
            self.client,
            precision=self.precision,
            territory=self.territory,
        )

        result = forecast.get_combined_coverage(indicator_names, runs)
        pd.testing.assert_frame_equal(result, expected_result)


class TestArpegeForecast(unittest.TestCase):
    def setUp(self):
        self.territory = "EUROPE"
        self._api_key = "fake_api_key"
        self.token = "fake_token"
        self.application_id = "fake_app_id"
        self.client = MeteoFranceClient(token=self.token)

    @patch("meteole._arpege.ArpegeForecast.get_capabilities")
    def test_initialization(self, mock_get_capabilities):
        territory = "EUROPE"
        api_key = "test_api_key"
        token = "test_token"
        application_id = "test_app_id"

        client = MeteoFranceClient(api_key=api_key, token=token, application_id=application_id, certs_path="toto")

        arpege_forecast = ArpegeForecast(
            client,
            territory=territory,
        )

        self.assertEqual(arpege_forecast.territory, territory)
        self.assertEqual(arpege_forecast.precision, ArpegeForecast.RELATION_TERRITORY_TO_PREC_ARPEGE[territory])
        self.assertEqual(arpege_forecast._client._verify, "toto")
        self.assertEqual(arpege_forecast._client._api_key, api_key)
        self.assertEqual(arpege_forecast._client._token, token)
        self.assertEqual(arpege_forecast._client._application_id, application_id)
        self.assertEqual(arpege_forecast.MODEL_NAME, "arpege")
        self.assertEqual(len(arpege_forecast.INDICATORS), 47)
        # mock_get_capabilities.assert_called_once()

    @patch("meteole._arpege.ArpegeForecast.get_capabilities")
    def test_validate_parameters(self, mock_get_capabilities):
        valid_territory = "EUROPE"
        invalid_territory = "INVALID_TERRITORY"

        # Test with a valid territory
        client = MeteoFranceClient(api_key="toto")
        arpege_forecast = ArpegeForecast(client, territory=valid_territory)

        try:
            arpege_forecast._validate_parameters()
        except ValueError:
            self.fail("_validate_parameters raised ValueError unexpectedly with valid territory!")

        # Test with an invalid territory
        arpege_forecast.territory = invalid_territory
        with self.assertRaises(ValueError):
            arpege_forecast._validate_parameters()

    @patch("meteole._arpege.ArpegeForecast.get_capabilities")
    @patch("meteole.clients.MeteoFranceClient._connect")
    def test_entry_point(self, mock_MeteoFranceClient_connect, mock_get_capabilities):
        territory = "EUROPE"
        arpege_forecast = ArpegeForecast(self.client, territory=territory)
        expected_entry_point = f"wcs/MF-NWP-GLOBAL-ARPEGE-{ArpegeForecast.PRECISION_FLOAT_TO_STR[ArpegeForecast.RELATION_TERRITORY_TO_PREC_ARPEGE[territory]]}-{territory}-WCS"
        self.assertEqual(arpege_forecast._entry_point, expected_entry_point)


class TestGetAvailableFeature(unittest.TestCase):
    def setUp(self):
        self.grid_axis = [
            {
                "gmlrgrid:GeneralGridAxis": {
                    "gmlrgrid:gridAxesSpanned": "time",
                    "gmlrgrid:coefficients": "3600 7200 10800",
                }
            },
            {
                "gmlrgrid:GeneralGridAxis": {
                    "gmlrgrid:gridAxesSpanned": "height",
                    "gmlrgrid:coefficients": "100 200 300",
                }
            },
            {
                "gmlrgrid:GeneralGridAxis": {
                    "gmlrgrid:gridAxesSpanned": "pressure",
                    "gmlrgrid:coefficients": "1000 2000 3000",
                }
            },
        ]

    def test_get_available_feature_time(self):
        result = AromeForecast._get_available_feature(self.grid_axis, "time")
        self.assertEqual(result, [3600, 7200, 10800])

    def test_get_available_feature_height(self):
        result = AromeForecast._get_available_feature(self.grid_axis, "height")
        self.assertEqual(result, [100, 200, 300])

    def test_get_available_feature_pressure(self):
        result = AromeForecast._get_available_feature(self.grid_axis, "pressure")
        self.assertEqual(result, [1000, 2000, 3000])

    def test_get_available_feature_not_found(self):
        result = AromeForecast._get_available_feature(self.grid_axis, "nonexistent")
        self.assertEqual(result, [])
