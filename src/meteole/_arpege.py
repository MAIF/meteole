from __future__ import annotations

from typing import Any, final

from meteole.clients import BaseClient, MeteoFranceClient
from meteole.forecast import WeatherForecast

AVAILABLE_ARPEGE_TERRITORY: list[str] = ["EUROPE", "GLOBE", "ATOURX", "EURAT"]

ARPEGE_INSTANT_INDICATORS: list[str] = [
    "GEOMETRIC_HEIGHT__GROUND_OR_WATER_SURFACE",
    "BRIGHTNESS_TEMPERATURE__GROUND_OR_WATER_SURFACE",
    "CONVECTIVE_AVAILABLE_POTENTIAL_ENERGY__GROUND_OR_WATER_SURFACE",
    "SPECIFIC_CLOUD_ICE_WATER_CONTENT__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "SPECIFIC_CLOUD_ICE_WATER_CONTENT__ISOBARIC_SURFACE",
    "WIND_SPEED_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "WIND_SPEED__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "WIND_SPEED__ISOBARIC_SURFACE",
    "RELATIVE_HUMIDITY__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "RELATIVE_HUMIDITY__ISOBARIC_SURFACE",
    "PLANETARY_BOUNDARY_LAYER_HEIGHT__GROUND_OR_WATER_SURFACE",
    "LOW_CLOUD_COVER__GROUND_OR_WATER_SURFACE",
    "HIGH_CLOUD_COVER__GROUND_OR_WATER_SURFACE",
    "MEDIUM_CLOUD_COVER__GROUND_OR_WATER_SURFACE",
    "PRESSURE__GROUND_OR_WATER_SURFACE",
    "PRESSURE__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "PRESSURE__MEAN_SEA_LEVEL",
    "ABSOLUTE_VORTICITY__ISOBARIC_SURFACE",
    "DEW_POINT_TEMPERATURE__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "DEW_POINT_TEMPERATURE__ISOBARIC_SURFACE",
    "TURBULENT_KINETIC_ENERGY__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "TURBULENT_KINETIC_ENERGY__ISOBARIC_SURFACE",
    "MAXIMUM_TEMPERATURE__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "MINIMUM_TEMPERATURE__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "PSEUDO_ADIABATIC_POTENTIAL_TEMPERATURE__ISOBARIC_SURFACE",
    "POTENTIAL_VORTICITY__ISOBARIC_SURFACE",
    "TEMPERATURE__GROUND_OR_WATER_SURFACE",
    "TEMPERATURE__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "TEMPERATURE__ISOBARIC_SURFACE",
    "U_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "U_COMPONENT_OF_WIND__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "U_COMPONENT_OF_WIND__ISOBARIC_SURFACE",
    "U_COMPONENT_OF_WIND__POTENTIAL_VORTICITY_SURFACE_1500",
    "U_COMPONENT_OF_WIND__POTENTIAL_VORTICITY_SURFACE_2000",
    "VERTICAL_VELOCITY_PRESSURE__ISOBARIC_SURFACE",
    "V_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "V_COMPONENT_OF_WIND__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",
    "V_COMPONENT_OF_WIND__ISOBARIC_SURFACE",
    "V_COMPONENT_OF_WIND__POTENTIAL_VORTICITY_SURFACE_1500",
    "V_COMPONENT_OF_WIND__POTENTIAL_VORTICITY_SURFACE_2000",
    "GEOPOTENTIAL__ISOBARIC_SURFACE",
    "TOTAL_CLOUD_COVER__GROUND_OR_WATER_SURFACE",
]

ARPEGE_OTHER_INDICATORS: list[str] = [
    "TOTAL_WATER_PRECIPITATION__GROUND_OR_WATER_SURFACE",
    "TOTAL_SNOW_PRECIPITATION__GROUND_OR_WATER_SURFACE",
    "TOTAL_PRECIPITATION__GROUND_OR_WATER_SURFACE",
    "DOWNWARD_SHORT_WAVE_RADIATION_FLUX__GROUND_OR_WATER_SURFACE",
    "SHORT_WAVE_RADIATION_FLUX__GROUND_OR_WATER_SURFACE",
]


@final
class ArpegeForecast(WeatherForecast):
    """Access the ARPEGE numerical weather forecast data from Meteo-France API.

    Doc:
        - https://portail-api.meteofrance.fr/web/fr/api/arpege

    Attributes:
        territory: Covered area (e.g., FRANCE, ANTIL, ...).
        precision: Precision value of the forecast.
        capabilities: DataFrame containing details on all available coverage ids.
    """

    # Model constants
    MODEL_NAME: str = "arpege"
    INDICATORS: list[str] = ARPEGE_INSTANT_INDICATORS + ARPEGE_OTHER_INDICATORS
    INSTANT_INDICATORS: list[str] = ARPEGE_INSTANT_INDICATORS
    BASE_ENTRY_POINT: str = "wcs/MF-NWP-GLOBAL-ARPEGE"
    DEFAULT_TERRITORY: str = "EUROPE"
    RELATION_TERRITORY_TO_PREC_ARPEGE: dict[str, float] = {"EUROPE": 0.1, "GLOBE": 0.25, "ATOURX": 0.1, "EURAT": 0.05}
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
