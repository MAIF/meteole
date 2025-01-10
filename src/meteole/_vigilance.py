from __future__ import annotations

import logging
from io import BytesIO
from typing import Any, final

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
from requests import Response

from meteole.clients import BaseClient, MeteoFranceClient
from meteole.errors import MissingDataError

logger = logging.getLogger(__name__)


@final
class Vigilance:
    """Easy access to the vigilance data of Meteo-France.

    Resources are:
    - textesvigilance
    - cartevigilance

    Docs:
    - https://portail-api.meteofrance.fr/web/fr/api/DonneesPubliquesVigilance
    - https://donneespubliques.meteofrance.fr/client/document/descriptiftechnique_vigilancemetropole_
        donneespubliques_v4_20230911_307.pdf
    """

    API_VERSION: str = "v1"
    VIGILANCE_BASE_PATH: str = "DPVigilance/"
    PHENOMENO_IDS: dict[str, str] = {
        "1": "wind",
        "2": "rain",
        "3": "storm",
        "4": "flood",
        "5": "snow_ice",
        "6": "heat_wave",
        "7": "extreme_cold",
        "8": "avalanches",
        "9": "waves_submergence",
    }

    def __init__(
        self,
        client: BaseClient | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize attributes"""
        if client is not None:
            self._client = client
        else:
            # Try to instantiate it (can be user friendly)
            self._client = MeteoFranceClient(**kwargs)

    def get_bulletin(self) -> dict[str, Any]:
        """Retrieve the vigilance bulletin.

        Returns:
            Dictionary representing the vigilance bulletin
        """

        path: str = self.VIGILANCE_BASE_PATH + self.API_VERSION + "/textesvigilance/encours"
        logger.debug(f"GET {path}")

        try:
            resp: Response = self._client.get(path)
            return resp.json()

        except MissingDataError as e:
            if "no matching blob" in str(e):
                logger.warning("Ongoing vigilance requires no publication")
            else:
                logger.error(f"Unexpected error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {}

    def get_map(self) -> dict[str, Any]:
        """Get the vigilance map with predicted risk displayed.

        Returns:
            Dictionary with the predicted risk.
        """
        path: str = self.VIGILANCE_BASE_PATH + self.API_VERSION + "/cartevigilance/encours"
        logger.debug(f"GET {path}")

        resp: Response = self._client.get(path)

        return resp.json()

    def get_phenomenon(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Get risk prediction by phenomenon and by domain.

        Returns:
            Tuple of:
                A DataFrame with phenomenon by id
                A DataFrame with phenomenon by domain
        """
        df_carte = pd.DataFrame(self.get_map())
        periods_data = df_carte.loc["periods", "product"]
        df_periods = pd.json_normalize(periods_data)

        df_j = df_periods[df_periods["echeance"] == "J"]
        df_j1 = df_periods[df_periods["echeance"] == "J1"]

        df_phenomenon_j = pd.json_normalize(df_j["per_phenomenon_items"].explode())
        df_phenomenon_j1 = pd.json_normalize(df_j1["per_phenomenon_items"].explode())
        df_phenomenon_j["echeance"] = "J"
        df_phenomenon_j1["echeance"] = "J1"

        df_phenomenon = pd.concat([df_phenomenon_j, df_phenomenon_j1]).reset_index(drop=True)
        df_phenomenon["phenomenon_libelle"] = df_phenomenon["phenomenon_id"].map(self.PHENOMENO_IDS)

        df_timelaps_j = pd.json_normalize(df_j["timelaps.domain_ids"].explode())
        df_timelaps_j1 = pd.json_normalize(df_j1["timelaps.domain_ids"].explode())
        df_timelaps_j["echeance"] = "J"
        df_timelaps_j1["echeance"] = "J1"

        df_timelaps = pd.concat([df_timelaps_j, df_timelaps_j1]).reset_index(drop=True)

        return df_phenomenon, df_timelaps

    def get_vignette(self) -> None:
        """Get png file."""
        path: str = self.VIGILANCE_BASE_PATH + self.API_VERSION + "/vignettenationale-J-et-J1/encours"

        logger.debug(f"GET {path}")
        resp: Response = self._client.get(path)

        if resp.status_code == 200:
            content: str | None = resp.headers.get("content-disposition")
            if content is not None:
                filename: str = content.split("filename=")[1]
                filename = filename.strip('"')

            with open(filename, "wb") as f:
                f.write(resp.content)

            img = mpimg.imread(BytesIO(resp.content), format="png")
            plt.imshow(img)
            plt.axis("off")
            plt.show()
        else:
            resp.raise_for_status()
