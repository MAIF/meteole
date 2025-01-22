from importlib.metadata import version

from meteole._arome import AromeForecast
from meteole._arome_instantane import AromeInstantaneForecast
from meteole._arpege import ArpegeForecast
from meteole._vigilance import Vigilance

__all__ = ["AromeForecast", "AromeInstantaneForecast", "ArpegeForecast", "Vigilance"]

__version__ = version("meteole")
