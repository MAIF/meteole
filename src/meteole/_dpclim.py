from __future__ import annotations

import logging
from typing import final

from meteole.clients import BaseClient, MeteoFranceClient
from meteole.climat import WeatherObservation

logger = logging.getLogger(__name__)


@final
class DPClim(WeatherObservation):
    """Access the "Données Climatologiques" data from Meteo-France API.

    Doc:
        - https://https://portail-api.meteofrance.fr/web/fr/api/DonneesPubliquesClimatologie
    """

    # Model constants
    MODEL_NAME: str = "DPClim"
    BASE_ENTRY_POINT: str = "DPClim"
    CLIENT_CLASS: type[BaseClient] = MeteoFranceClient

    def _validate_parameters(self) -> None:
        """Check the territory and the precision parameters.

        Raise:
            ValueError: At least, one parameter is not good.
        """
        if self.frequency not in ("6m", "hourly", "daily", "decade", "monthly"):
            raise ValueError("Parameter `frequency` must be in ('6m','hourly', 'daily', 'decade', 'monthly').")
