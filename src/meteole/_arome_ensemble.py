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
class AromePEForecast(WeatherForecast):
    """Access the PE-AROME ensemble forecast data from Meteo-France API."""

    MODEL_NAME: str = "pearome"
    BASE_ENTRY_POINT: str = "wcs/MF-NWP-HIGHRES-PEARO"
    MODEL_TYPE: str = "ENSEMBLE"
    ENSEMBLE_NUMBERS: int = 25
    DEFAULT_TERRITORY: str = "FRANCE"
    CLIENT_CLASS: type[BaseClient] = MeteoFranceClient

    def __init__(self, client=None, **kwargs):
        super().__init__(client, precision=0.025, **kwargs)

    def _validate_parameters(self) -> None:
        """Check the territory and the precision parameters.

        Raise:
            ValueError: At least, one parameter is not good.
        """
        if self.precision != 0.025:
            raise ValueError("Parameter `precision` must be 0.025")

        if self.territory not in AVAILABLE_AROME_TERRITORY:
            raise ValueError(f"Parameter `territory` must be in {AVAILABLE_AROME_TERRITORY}")
