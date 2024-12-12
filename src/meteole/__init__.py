from meteole.arome import AromeForecast  # noqa
from meteole.arpege import ArpegeForecast  # noqa
from meteole.vigilance import Vigilance  # noqa

from importlib.metadata import version

__version__ = version("meteole")


import logging


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
