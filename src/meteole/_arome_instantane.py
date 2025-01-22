from __future__ import annotations

import logging
from typing import final

from meteole.clients import BaseClient, MeteoFranceClient
from meteole.forecast import WeatherForecast

logger = logging.getLogger(__name__)

AVAILABLE_AROME_TERRITORY: list[str] = [
    "FRANCE",
    "NCALED",
    "INDIEN",
    "POLYN",
    "GUYANE",
    "ANTIL",
]

AROME_INSTANT_INDICATORS: list[str] = [
    "TPW_27315_HEIGHT__LEVEL_OF_ADIABATIC_CONDESATION",
    "TPW_27415_HEIGHT__LEVEL_OF_ADIABATIC_CONDESATION ",
    "TPW_27465_HEIGHT__LEVEL_OF_ADIABATIC_CONDESATION",
    "BRIGHTNESS_TEMPERATURE__GROUND_OR_WATER_SURFACE",
    "CONVECTIVE_AVAILABLE_POTENTIAL_ENERGY__GROUND_OR_WATER_SURFACE",
    "DIAG_GRELE__GROUND_OR_WATER_SURFACE",
    "TOTAL_WATER_PRECIPITATION__GROUND_OR_WATER_SURFACE",
    "WIND_SPEED_GUST_15MIN__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "WIND_SPEED_MAXIMUM_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "WIND_SPEED_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "RELATIVE_HUMIDITY__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "MOCON__GROUND_OR_WATER_SURFACE",
    "LOW_CLOUD_COVER__GROUND_OR_WATER_SURFACE",
    "SEVERE_PRECIPITATION_TYPE_15_MIN__GROUND_OR_WATER_SURFACE",
    "PRECIPITATION_TYPE_15_MIN__GROUND_OR_WATER_SURFACE",
    "PRESSURE__SEA_SURFACE",
    "REFLECTIVITY_MAX_DBZ__GROUND_OR_WATER_SURFACE",
    "DEW_POINT_TEMPERATURE__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "TOTAL_PRECIPITATION_RATE__GROUND_OR_WATER_SURFACE",
    "TEMPERATURE__GROUND_OR_WATER_SURFACE",
    "TEMPERATURE__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "U_COMPONENT_OF_WIND_GUST_15MIN__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "U_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "VISIBILITY_MINI_PRECIP_15MIN__GROUND_OR_WATER_SURFACE",
    "VISIBILITY_MINI_15MIN__GROUND_OR_WATER_SURFACE",
    "V_COMPONENT_OF_WIND_GUST_15MIN__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "V_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "WETB_TEMPERATURE__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
]


AROME_OTHER_INDICATORS: list[str] = [
    "TOTAL_WATER_PRECIPITATION__GROUND_OR_WATER_SURFACE",
    "TOTAL_SNOW_PRECIPITATION__GROUND_OR_WATER_SURFACE",
    "TOTAL_PRECIPITATION__GROUND_OR_WATER_SURFACE",
    "WIND_SPEED_GUST_15MIN__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "WIND_SPEED_MAXIMUM_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "GRAUPEL__GROUND_OR_WATER_SURFACE",
    "HAIL__GROUND_OR_WATER_SURFACE",
    "SOLID_PRECIPITATION__GROUND_OR_WATER_SURFACE",
]


@final
class AromeInstantaneForecast(WeatherForecast):
    """Access the AROME numerical weather forecast data from Meteo-France API.

    Doc:
        - https://portail-api.meteofrance.fr/web/fr/api/arome

    Attributes:
        territory: Covered area (e.g., FRANCE, ANTIL, ...).
        precision: Precision value of the forecast.
        capabilities: DataFrame containing details on all available coverage ids.
    """

    # Model constants
    MODEL_NAME: str = "aromepi"
    INDICATORS: list[str] = AROME_INSTANT_INDICATORS + AROME_OTHER_INDICATORS
    INSTANT_INDICATORS: list[str] = AROME_INSTANT_INDICATORS
    BASE_ENTRY_POINT: str = "wcs/MF-NWP-HIGHRES-AROMEPI"
    DEFAULT_TERRITORY: str = "FRANCE"
    DEFAULT_PRECISION: float = 0.01
    CLIENT_CLASS: type[BaseClient] = MeteoFranceClient

    def _validate_parameters(self) -> None:
        """Check the territory and the precision parameters.

        Raise:
            ValueError: At least, one parameter is not good.
        """
        if self.precision not in [0.01, 0.025]:
            raise ValueError("Parameter `precision` must be in (0.01, 0.025). It is inferred from argument `territory`")

        if self.territory not in AVAILABLE_AROME_TERRITORY:
            raise ValueError(f"Parameter `territory` must be in {AVAILABLE_AROME_TERRITORY}")
