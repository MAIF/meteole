import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from meteole import const
from meteole._arome import AromeForecast
from meteole._arpege import RELATION_TERRITORY_TO_PREC_ARPEGE, ArpegeForecast


class TestAromeForecast(unittest.TestCase):
    def setUp(self):
        self.precision = 0.01
        self.territory = "FRANCE"
        self.api_key = "fake_api_key"
        self.token = "fake_token"
        self.application_id = "fake_app_id"
        self.cache_dir = tempfile.mkdtemp(prefix="test_cache_")

    @patch("meteole._arome.AromeForecast.get_capabilities")
    def test_initialization(self, mock_get_capabilities):
        mock_get_capabilities.return_value = None

        forecast = AromeForecast(
            precision=self.precision,
            territory=self.territory,
            api_key=self.api_key,
            token=self.token,
            application_id=self.application_id,
            cache_dir=self.cache_dir,
        )

        self.assertEqual(forecast.precision, self.precision)
        self.assertEqual(forecast.territory, self.territory)
        self.assertEqual(forecast.api_key, self.api_key)
        self.assertEqual(forecast.token, self.token)
        self.assertEqual(forecast.application_id, self.application_id)
        self.assertEqual(forecast.cache_dir, Path(self.cache_dir))
        self.assertEqual(forecast.model_name, "arome")
        self.assertEqual(forecast.run_frequency, 3)
        self.assertEqual(len(forecast.indicators), 19)
        mock_get_capabilities.assert_called_once()

    def test_invalid_precision(self):
        with self.assertRaises(ValueError):
            AromeForecast(precision=0.1)

    def test_invalid_territory(self):
        with self.assertRaises(ValueError):
            AromeForecast(territory="INVALID")

    @patch("meteole._arome.AromeForecast._get_request")
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
            precision=self.precision,
            territory=self.territory,
            api_key=self.api_key,
            token=self.token,
            application_id=self.application_id,
            cache_dir=self.cache_dir,
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

    @patch("meteole._arome.AromeForecast._get_request")
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
            precision=self.precision,
            territory=self.territory,
            api_key=self.api_key,
            token=self.token,
            application_id=self.application_id,
            cache_dir=self.cache_dir,
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
    @patch("meteole._arome.AromeForecast._get_request")
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
            precision=self.precision,
            territory=self.territory,
            api_key=self.api_key,
            token=self.token,
            application_id=self.application_id,
            cache_dir=self.cache_dir,
        )

        description = forecast._get_coverage_description("coverage_1")
        self.assertIn("wcs:CoverageDescriptions", description)

    @patch("meteole._arome.AromeForecast.get_capabilities")
    @patch("meteole._arome.AromeForecast._get_request")
    def test_get_coverage_file(self, mock_get_request, mock_get_capabilities):
        mock_response = MagicMock()
        mock_response.content = b"fake_data"
        mock_get_request.return_value = mock_response
        mock_get_capabilities.return_value = None

        forecast = AromeForecast(
            precision=self.precision,
            territory=self.territory,
            api_key=self.api_key,
            token=self.token,
            application_id=self.application_id,
            cache_dir=self.cache_dir,
        )

        coverage_id = "coverage_1"
        forecast._get_coverage_file(
            coverage_id=coverage_id,
            height=2,
            forecast_horizon_in_seconds=0,
            lat=(37.5, 55.4),
            long=(-12, 16),
        )

        import os

        expected_path = Path(os.getcwd()) / coverage_id / "2m_0Z_37.5-55.4_-12-16.grib"
        self.assertTrue(expected_path.exists())

        expected_path.unlink()

    @patch("meteole._arome.AromeForecast.get_capabilities")
    @patch("meteole._arome.AromeForecast._transform_grib_to_df")
    @patch("meteole._arome.AromeForecast._get_coverage_file")
    def test_get_data_single_forecast(self, mock_get_coverage_file, mock_transform_grib_to_df, mock_get_capabilities):
        mock_transform_grib_to_df.return_value = pd.DataFrame({"data": [1, 2, 3], "heightAboveGround": ["1", "2", "3"]})

        forecast = AromeForecast(
            precision=self.precision,
            territory=self.territory,
            api_key=self.api_key,
            token=self.token,
            application_id=self.application_id,
            cache_dir=self.cache_dir,
        )

        df = forecast._get_data_single_forecast(
            coverage_id="coverage_1",
            height=2,
            pressure=None,
            forecast_horizon=0,
            lat=(37.5, 55.4),
            long=(-12, 16),
        )

        self.assertTrue("data" in df.columns)

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
            precision=self.precision,
            territory=self.territory,
            api_key=self.api_key,
            token=self.token,
            application_id=self.application_id,
            cache_dir=self.cache_dir,
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


class TestArpegeForecast(unittest.TestCase):
    def setUp(self):
        self.territory = "EUROPE"
        self.api_key = "fake_api_key"
        self.token = "fake_token"
        self.application_id = "fake_app_id"

    @patch("meteole._arpege.ArpegeForecast.get_capabilities")
    def test_initialization(self, mock_get_capabilities):
        territory = "EUROPE"
        api_key = "test_api_key"
        token = "test_token"
        application_id = "test_app_id"

        arpege_forecast = ArpegeForecast(
            territory=territory, api_key=api_key, token=token, application_id=application_id, cache_dir="toto"
        )

        self.assertEqual(arpege_forecast.territory, territory)
        self.assertEqual(arpege_forecast.precision, RELATION_TERRITORY_TO_PREC_ARPEGE[territory])
        self.assertEqual(arpege_forecast.cache_dir, Path("toto"))
        self.assertEqual(arpege_forecast.api_key, api_key)
        self.assertEqual(arpege_forecast.token, token)
        self.assertEqual(arpege_forecast.application_id, application_id)
        self.assertEqual(arpege_forecast.model_name, "arpege")
        self.assertEqual(arpege_forecast.run_frequency, 6)
        self.assertEqual(len(arpege_forecast.indicators), 47)
        mock_get_capabilities.assert_called_once()

    @patch("meteole._arpege.ArpegeForecast.get_capabilities")
    def test_validate_parameters(self, mock_get_capabilities):
        valid_territory = "EUROPE"
        invalid_territory = "INVALID_TERRITORY"

        # Test with a valid territory
        arpege_forecast = ArpegeForecast(territory=valid_territory, api_key="toto")

        try:
            arpege_forecast._validate_parameters()
        except ValueError:
            self.fail("_validate_parameters raised ValueError unexpectedly with valid territory!")

        # Test with an invalid territory
        arpege_forecast.territory = invalid_territory
        with self.assertRaises(ValueError):
            arpege_forecast._validate_parameters()

    @patch("meteole._arpege.ArpegeForecast.get_capabilities")
    @patch("meteole.client.MeteoFranceClient.connect")
    def test_entry_point(self, mock_MeteoFranceClient_connect, mock_get_capabilities):
        territory = "EUROPE"
        arpege_forecast = ArpegeForecast(territory=territory)
        expected_entry_point = f"wcs/MF-NWP-GLOBAL-ARPEGE-{const.PRECISION_FLOAT_TO_STR[RELATION_TERRITORY_TO_PREC_ARPEGE[territory]]}-{territory}-WCS"
        self.assertEqual(arpege_forecast.entry_point, expected_entry_point)


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
