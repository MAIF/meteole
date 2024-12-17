"""The interface for the observational data from the meteo-France API.

See :
- https://portail-api.meteofrance.fr/web/fr/api/arome
"""

import logging

from meteole import const, forecast

logger = logging.getLogger(__name__)

AVAILABLE_AROME_TERRITORY = [
    "FRANCE",
    "NCALED",
    "INDIEN",
    "POLYN",
    "GUYANE",
    "ANTIL",
]

AROME_INSTANT_INDICATORS = [
    "GEOMETRIC_HEIGHT__GROUND_OR_WATER_SURFACE",
    "BRIGHTNESS_TEMPERATURE__GROUND_OR_WATER_SURFACE",
    "CONVECTIVE_AVAILABLE_POTENTIAL_ENERGY__GROUND_OR_WATER_SURFACE",
    "WIND_SPEED_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "WIND_SPEED__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "RELATIVE_HUMIDITY__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "LOW_CLOUD_COVER__GROUND_OR_WATER_SURFACE",
    "HIGH_CLOUD_COVER__GROUND_OR_WATER_SURFACE",
    "MEDIUM_CLOUD_COVER__GROUND_OR_WATER_SURFACE",
    "PRESSURE__GROUND_OR_WATER_SURFACE",
    "TOTAL_PRECIPITATION_RATE__GROUND_OR_WATER_SURFACE",
    "TEMPERATURE__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "U_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "U_COMPONENT_OF_WIND__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "V_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "V_COMPONENT_OF_WIND__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
]

AROME_OTHER_INDICATORS = [
    "TOTAL_WATER_PRECIPITATION__GROUND_OR_WATER_SURFACE",
    "TOTAL_SNOW_PRECIPITATION__GROUND_OR_WATER_SURFACE",
    "TOTAL_PRECIPITATION__GROUND_OR_WATER_SURFACE",
]


class AromeForecast(forecast.Forecast):
    """Access the AROME numerical Forecast."""

    api_version = "1.0"
    base_url = const.API_BASE_URL + "arome/" + api_version

    def __init__(
        self,
        api_key: str | None = None,
        territory: str = "FRANCE",
        precision: float = 0.01,
        token: str | None = None,
        application_id: str | None = None,
        cache_dir: str | None = None,
    ):
        """
        Init the AromeForecast object.

        Parameters
        ----------
        precision : {0.01, 0.025}, optional
            the resolution of the AROME Model, by default 0.01
        territory : str, optional
            The AROME territory to fetch, by default "FRANCE"
        api_key : str | None, optional
            The API Key, by default None
        token : str | None, optional
            The API Token, by default None
        application_id : str | None, optional
            The Application ID, by default None
        cache_dir : str | None, optional
            The path to the caching directory, by default None.
            If None, the cache directory is set to "/tmp/cache".

        Note
        ----
        See :class:`.MeteoFranceClient` for the parameters `api_key`, `token` and `application_id`.

        The available territories are listed in :data:`.AVAILABLE_TERRITORY`.

        """
        super().__init__(api_key, token, territory, precision, application_id, cache_dir)

    def _validate_parameters(self):
        """Assert the parameters are valid."""
        if self.precision not in [0.01, 0.025]:
            raise ValueError("Parameter `precision` must be in (0.01, 0.025). It is inferred from argument `territory`")
        if self.territory not in AVAILABLE_AROME_TERRITORY:
            raise ValueError(f"Parameter `territory` must be in {AVAILABLE_AROME_TERRITORY}")

    @property
    def run_frequency(self):
        """Update frequency of the inference"""
        return 3

    @property
    def model_name(self):
        """Name of the model (lower case)"""
        return "arome"

    @property
    def entry_point(self):
        """The entry point to AROME service."""
        return f"wcs/MF-NWP-HIGHRES-AROME-{const.PRECISION_FLOAT_TO_STR[self.precision]}-{self.territory}-WCS"

    @property
    def indicators(self):
        """List of all indicators (instant and non-instant)"""
        return AROME_INSTANT_INDICATORS + AROME_OTHER_INDICATORS

    @property
    def instant_indicators(self):
        """List of instant indicators"""
        return AROME_INSTANT_INDICATORS
