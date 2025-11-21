from __future__ import annotations

import logging
from typing import Any, final

from meteole.clients import BaseClient, MeteoFranceClient
from meteole.forecast import WeatherForecast

logger = logging.getLogger(__name__)

AVAILABLE_ARPEGE_TERRITORY: list[str] = ["EUROPE", "GLOBE"]


@final
class ArpegePEForecast(WeatherForecast):
    """Access the ARPEGE numerical weather forecast data from Meteo-France API.

    Doc:
        - https://portail-api.meteofrance.fr/web/fr/api/pe-arpege

    Attributes:
        territory: Covered area (e.g., FRANCE, EUROPE, ...).
        precision: Precision value of the forecast.
        capabilities: DataFrame containing details on all available coverage ids.
    """

    MODEL_NAME: str = "pearpege"
    BASE_ENTRY_POINT: str = "wcs/MF-NWP-GLOBAL-PEARP"
    MODEL_TYPE: str = "ENSEMBLE"
    ENSEMBLE_NUMBERS: int = 35
    DEFAULT_TERRITORY: str = "EUROPE"
    RELATION_TERRITORY_TO_PREC_ARPEGE: dict[str, float] = {"EUROPE": 0.1, "GLOBE": 0.25}
    CLIENT_CLASS: type[BaseClient] = MeteoFranceClient

    def __init__(
        self,
        client: BaseClient | None = None,
        *,
        territory: str = "EUROPE",
        **kwargs: Any,
    ):
        """Initializes an ArpegeForecast object.

        The `precision` of the forecast is inferred from the specified `territory`.

        Args:
            territory: The ARPEGE territory to fetch. Defaults to "EUROPE".
            api_key: The API key for authentication. Defaults to None.
            token: The API token for authentication. Defaults to None.
            application_id: The Application ID for authentication. Defaults to None.

        Notes:
            - See `MeteoFranceClient` for additional details on the parameters `api_key`, `token`,
                and `application_id`.
            - Available territories are listed in the `AVAILABLE_TERRITORY` constant.
        """
        super().__init__(
            client=client,
            territory=territory,
            precision=self.RELATION_TERRITORY_TO_PREC_ARPEGE[territory],
            **kwargs,
        )

    def _validate_parameters(self) -> None:
        """Check the territory and the precision parameters.

        Raise:
            ValueError: At least, one parameter is not good.
        """
        if self.territory not in AVAILABLE_ARPEGE_TERRITORY:
            raise ValueError(f"The parameter precision must be in {AVAILABLE_ARPEGE_TERRITORY}")
