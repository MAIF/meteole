import logging
from io import BytesIO
from typing import Tuple

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd

from meteole import client, const
from meteole.errors import MissingDataError

logger = logging.getLogger(__name__)


class Vigilance(client.MeteoFranceClient):
    """Wrapper around the meteo-France API for the vigilance data.
    Ressources are:
    - textesvigilance
    - cartevigilance

    Documentation
    -------------
    See:
    - https://portail-api.meteofrance.fr/web/fr/api/DonneesPubliquesVigilance
    - https://donneespubliques.meteofrance.fr/client/document/descriptiftechnique_vigilancemetropole_donneespubliques_v4_20230911_307.pdf
    """

    base_url = const.API_BASE_URL + "DPVigilance/"
    version = "v1"

    def __init__(
        self,
        api_key: str | None = None,
        token: str | None = None,
        application_id: str | None = None,
    ):
        """
        Init the Vigilance object.
         Parameters
        ----------
        api_key : str | None, optional
            The API Key, by default None
        token : str | None, optional
            The API Token, by default None
        application_id : str | None, optional
            The Application ID, by default None
        Note
        ----
        See :class:`.MeteoFranceClient` for the parameters `api_key`, `token` and `application_id`.
        """

        super().__init__(api_key, token, application_id)

    def get_textes_vigilance(self) -> dict:
        """
        Get bulletin de vigilance

        Returns:
        --------
        dict: a Dict with bulletin de vigilance
        """

        url = self.base_url + self.version + "/textesvigilance/encours"
        logger.debug(f"GET {url}")
        try:
            req = self._get_request(url)
            return req.json()
        except MissingDataError as e:
            if "no matching blob" in e.message:
                logger.warning("La vigilance en cours ne nécessite pas de publication")
            else:
                logger.error(f"Unexpected error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {}

    def get_carte_vigilance(self) -> dict:
        """
        Get "carte" de Vigilance with risk prediction

        Returns:
        --------
        dict: a Dict with risk prediction
        """
        url = self.base_url + self.version + "/cartevigilance/encours"
        logger.debug(f"GET {url}")
        req = self._get_request(url)

        return req.json()

    def get_phenomenon(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        get risk prediction by phenomenon and by domain
        Returns:
        --------
        pd.DataFrame: a DataFrame with phenomenon by id
        pd.DataFrame: a DataFrame with phenomenon by domain
        """
        df_carte = pd.DataFrame(self.get_carte_vigilance())
        periods_data = df_carte.loc["periods", "product"]
        df_periods = pd.json_normalize(periods_data)

        df_j = df_periods[df_periods["echeance"] == "J"]
        df_j1 = df_periods[df_periods["echeance"] == "J1"]

        df_phenomenon_j = pd.json_normalize(df_j["per_phenomenon_items"].explode())
        df_phenomenon_j1 = pd.json_normalize(df_j1["per_phenomenon_items"].explode())
        df_phenomenon_j["echeance"] = "J"
        df_phenomenon_j1["echeance"] = "J1"

        df_phenomenon = pd.concat([df_phenomenon_j, df_phenomenon_j1]).reset_index(drop=True)
        df_phenomenon["phenomenon_libelle"] = df_phenomenon["phenomenon_id"].map(const.dict_phenomenon_id)

        df_timelaps_j = pd.json_normalize(df_j["timelaps.domain_ids"].explode())
        df_timelaps_j1 = pd.json_normalize(df_j1["timelaps.domain_ids"].explode())
        df_timelaps_j["echeance"] = "J"
        df_timelaps_j1["echeance"] = "J1"

        df_timelaps = pd.concat([df_timelaps_j, df_timelaps_j1]).reset_index(drop=True)

        return df_phenomenon, df_timelaps

    def get_vignette(self) -> None:
        """
        Get png
        """
        url = self.base_url + self.version + "/vignettenationale-J-et-J1/encours"

        logger.debug(f"GET {url}")
        req = self._get_request(url)

        if req.status_code == 200:
            filename = req.headers.get("content-disposition").split("filename=")[1]
            filename = filename.strip('"')

            with open(filename, "wb") as f:
                f.write(req.content)

            img = mpimg.imread(BytesIO(req.content), format="png")
            plt.imshow(img)
            plt.axis("off")
            plt.show()
        else:
            req.raise_for_status()
