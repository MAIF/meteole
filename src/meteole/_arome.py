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


@final
class AromeForecast(WeatherForecast):
    """Access the AROME numerical weather forecast data from Meteo-France API.

    Doc:
        - https://portail-api.meteofrance.fr/web/fr/api/arome

    Attributes:
        territory: Covered area (e.g., FRANCE, ANTIL, ...).
        precision: Precision value of the forecast.
        capabilities: DataFrame containing details on all available coverage ids.
    """

    # Model constants
    MODEL_NAME: str = "arome"
    BASE_ENTRY_POINT: str = "wcs/MF-NWP-HIGHRES-AROME"
    MODEL_TYPE: str = "DETER"
    ENSEMBLE_NUMBERS: int = 1
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
