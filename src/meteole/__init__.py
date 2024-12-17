import logging
from importlib.metadata import version

from meteole._arome import AromeForecast
from meteole._arpege import ArpegeForecast
from meteole._vigilance import Vigilance

__all__ = ["AromeForecast", "ArpegeForecast", "Vigilance"]

__version__ = version("meteole")


def setup_logger():
    """Setup logger with proper StreamHandler and formatter"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Créer un gestionnaire de flux (StreamHandler) pour afficher les logs dans la console
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)

    # Créer un formatteur et l'ajouter au gestionnaire
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    # Ajouter le gestionnaire au logger
    return logger.addHandler(handler)


logger = setup_logger()
