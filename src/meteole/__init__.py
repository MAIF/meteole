from importlib.metadata import version

from meteole._arome import AromeForecast
from meteole._arome_instantane import AromePIForecast
from meteole._arpege import ArpegeForecast
from meteole._vigilance import Vigilance

__all__ = ["AromeForecast", "AromePIForecast", "ArpegeForecast", "Vigilance"]

__version__ = version("meteole")
