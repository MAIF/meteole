import datetime as dt
import glob
import logging
import os
import shutil
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd
import xarray as xr
import xmltodict

from meteole import const
from meteole.client import MeteoFranceClient
from meteole.errors import MissingDataError

logger = logging.getLogger(__name__)


class Forecast(ABC, MeteoFranceClient):
    """
    Provides a unified interface to query AROME and ARPEGE endpoints

    Attributes
    ----------
    capabilities: pandas.DataFrame
        coverage dataframe containing the details of all available coverage_ids
    """

    api_version = "1.0"
    base_url = const.API_BASE_URL

    def __init__(
        self,
        api_key: str | None = None,
        token: str | None = None,
        territory: str = "FRANCE",
        precision: float = 0.01,
        application_id: str | None = None,
        cache_dir: str | None = None,
    ):
        """Init the Forecast object."""
        super().__init__(
            api_key=api_key,
            application_id=application_id,
            token=token,
        )

        if cache_dir is None:
            initial_cache_dir = tempfile.TemporaryDirectory().name
        else:
            initial_cache_dir = cache_dir

        self.cache_dir = Path(initial_cache_dir)

        self.territory = territory  # "FRANCE", "ANTIL", or others (see API doc)
        self.precision = precision
        self._validate_parameters()

        self.folderpath: Path | None = None
        self.get_capabilities()

    def get_capabilities(self) -> pd.DataFrame:
        "Returns the coverage dataframe containing the details of all available coverage_ids"

        logger.info("Fetching all available coverages...")

        capabilities = self._get_capabilities()
        df_capabilities = pd.DataFrame(capabilities["wcs:Capabilities"]["wcs:Contents"]["wcs:CoverageSummary"])
        df_capabilities = df_capabilities.rename(
            columns={
                "wcs:CoverageId": "id",
                "ows:Title": "title",
                "wcs:CoverageSubtype": "subtype",
            }
        )
        df_capabilities["indicator"] = [coverage_id.split("___")[0] for coverage_id in df_capabilities["id"]]
        df_capabilities["run"] = [
            coverage_id.split("___")[1].split("Z")[0] + "Z" for coverage_id in df_capabilities["id"]
        ]
        df_capabilities["interval"] = [
            coverage_id.split("___")[1].split("Z")[1].strip("_") for coverage_id in df_capabilities["id"]
        ]
        self.capabilities = df_capabilities

        nb_indicators = len(df_capabilities["indicator"].unique())
        nb_coverage_ids = df_capabilities.shape[0]
        runs = df_capabilities["run"].unique()

        logger.info(
            f"\n"
            f"\t Successfully fetched {nb_coverage_ids} coverages,\n"
            f"\t representing {nb_indicators} different indicators,\n"
            f"\t across the last {len(runs)} runs (from {runs.min()} to {runs.max()}).\n"
            f"\n"
            f"\t Default run for `get_coverage`: {runs.max()})"
        )

        return df_capabilities

    @staticmethod
    def _get_available_feature(grid_axis, feature_name):
        features = []
        feature_grid_axis = [
            ax for ax in grid_axis if ax["gmlrgrid:GeneralGridAxis"]["gmlrgrid:gridAxesSpanned"] == feature_name
        ]
        if feature_grid_axis:
            features = feature_grid_axis[0]["gmlrgrid:GeneralGridAxis"]["gmlrgrid:coefficients"].split(" ")
            features = [int(feature) for feature in features]
        return features

    def get_coverage_description(self, coverage_id: str) -> dict:
        """This endpoint returns the available axis (times, heights) to properly query coverage

        TODO: other informations can be fetched from this endpoint, not yet implemented.

        Args:
            coverage_id (str): use :meth:`get_capabilities()` to list all available coverage_id
        """

        # get coverage description
        description = self._get_coverage_description(coverage_id)
        grid_axis = description["wcs:CoverageDescriptions"]["wcs:CoverageDescription"]["gml:domainSet"][
            "gmlrgrid:ReferenceableGridByVectors"
        ]["gmlrgrid:generalGridAxis"]

        return {
            "forecast_horizons": [
                int(time / 3600) for time in self.__class__._get_available_feature(grid_axis, "time")
            ],
            "heights": self.__class__._get_available_feature(grid_axis, "height"),
            "pressures": self.__class__._get_available_feature(grid_axis, "pressure"),
        }

    def get_coverages(
        self,
        coverage_ids: list[str],
        lat: tuple = const.FRANCE_METRO_LATITUDES,
        long: tuple = const.FRANCE_METRO_LONGITUDES,
    ) -> pd.DataFrame:
        """
        Convenient function to quickly fetch a list of indicators using defaults `heights` and `forecast_horizons`

        For finer control over heights and forecast_horizons use :meth:`get_coverage`
        """
        coverages = [
            self.get_coverage(
                coverage_id,
                lat,
                long,
            )
            for coverage_id in coverage_ids
        ]

        return pd.concat(coverages, axis=0)

    def _get_coverage_id(
        self,
        indicator: str,
        run: str | None = None,
        interval: str | None = None,
    ) -> str:
        """
        Get a coverage_id from `capabilities`.

        Parameters:
        indicator (str): required.
        run (Optional[str]): Identifies the model inference. Defaults to latest if None. Format "YYYY-MM-DDTHH:MM:SSZ".
        interval (Optional[str]): aggregation period. Must be None for instant indicators, otherwise raises. Defaults to P1D for time-aggregated indicators like TOTAL_PRECIPITATION.

        Returns:
        str: coverage_id

        Raises:
        ValueError: If no or invalid 'indicator'
        ValueError: If invalid interval, or if missing interval when required
        """
        if not hasattr(self, "capabilities"):
            self.get_capabilities()

        capabilities = self.capabilities[self.capabilities["indicator"] == indicator]

        if indicator not in self.indicators:
            raise ValueError(f"Unknown `indicator` - checkout `{self.model_name}.indicators` to have the full list.")

        if run is None:
            run = capabilities.iloc[0]["run"]
            logger.info(f"Using latest `run={run}`.")

        try:
            dt.datetime.strptime(run, "%Y-%m-%dT%H.%M.%SZ")
        except ValueError as exc:
            raise ValueError(f"Run '{run}' is invalid. Expected format 'YYYY-MM-DDTHH.MM.SSZ'") from exc

        valid_runs = capabilities["run"].unique().tolist()
        if run not in valid_runs:
            raise ValueError(f"Run '{run}' is invalid. Valid runs : {valid_runs}")

        # handle interval
        valid_intervals = capabilities["interval"].unique().tolist()

        if indicator in self.instant_indicators:
            if interval is None:
                # no interval is expected for instant indicators
                pass
            else:
                raise ValueError(
                    f"interval={interval} is invalid. No interval is expected (=set to None) for instant indicator `{indicator}`."
                )
        else:
            if interval is None:
                interval = "P1D"
                logger.info(
                    f"`interval=None` is invalid  for non-instant indicators. Using default `interval={interval}`"
                )
            elif interval not in valid_intervals:
                raise ValueError(
                    f"interval={interval} is invalid  for non-instant indicators. `{indicator}`. Use valid intervals: {valid_intervals}"
                )

        coverage_id = f"{indicator}___{run}"

        if interval is not None:
            coverage_id += f"_{interval}"

        return coverage_id

    def get_coverage(
        self,
        indicator: str | None = None,
        lat: tuple = const.FRANCE_METRO_LATITUDES,
        long: tuple = const.FRANCE_METRO_LONGITUDES,
        heights: list[int] | None = None,
        pressures: list[int] | None = None,
        forecast_horizons: list[int] | None = None,
        run: str | None = None,
        interval: str | None = None,
        coverage_id: str = "",
    ) -> pd.DataFrame:
        """Returns the data associated with the coverage_id for the selected parameters.

        Args:
            coverage_id (str): coverage_id, get the list using :meth:`get_capabilities`
            lat (tuple): minimum and maximum latitude
            long (tuple): minimum and maximum longitude
            heights (list): heights in meters
            pressures (list): pressures in hPa
            forecast_horizons (list): list of integers, representing the forecast horizon in hours

        Returns:
            pd.DataFrame: The complete run for the specified execution.
        """
        # ensure we only have one of coverage_id, indicator
        if not bool(indicator) ^ bool(coverage_id):
            raise ValueError("Argument `indicator` or `coverage_id` need to be set (only one of them)")

        if indicator:
            coverage_id = self._get_coverage_id(indicator, run, interval)

        logger.debug(f"Using `coverage_id={coverage_id}`")

        axis = self.get_coverage_description(coverage_id)

        heights = self._raise_if_invalid_or_fetch_default("heights", heights, axis["heights"])
        pressures = self._raise_if_invalid_or_fetch_default("pressures", pressures, axis["pressures"])
        forecast_horizons = self._raise_if_invalid_or_fetch_default(
            "forecast_horizons", forecast_horizons, axis["forecast_horizons"]
        )

        df_list = [
            self._get_data_single_forecast(
                coverage_id=coverage_id,
                height=height if height != -1 else None,
                pressure=pressure if pressure != -1 else None,
                forecast_horizon=forecast_horizon,
                lat=lat,
                long=long,
            )
            for forecast_horizon in forecast_horizons
            for pressure in pressures
            for height in heights
        ]

        return pd.concat(df_list, axis=0).reset_index(drop=True)

    def _raise_if_invalid_or_fetch_default(
        self, param_name: str, inputs: list[int] | None, availables: list[int]
    ) -> list[int]:
        """
        Checks if the elements in `inputs` are in `availables` and raises a ValueError if not.
        If `inputs` is empty or None, uses the first element from `availables` as the default value.

        Args:
            param_name (str): The name of the parameter to validate.
            inputs (Optional[List[int]]): The list of inputs to validate.
            availables (List[int]): The list of available values.

        Returns:
            List[int]: The validated list of inputs or the default value.

        Raises:
            ValueError: If any of the inputs are not in `availables`.
        """
        if inputs:
            for input_value in inputs:
                if input_value not in availables:
                    raise ValueError(f"`{param_name}={inputs}` is invalid. Available {param_name}: {availables}")
        else:
            inputs = availables[:1] or [
                -1
            ]  # using [-1] make sure we have an iterable. Using None makes things too complicated with mypy...
            if inputs[0] != -1:
                logger.info(f"Using `{param_name}={inputs}`")
        return inputs

    @property
    @abstractmethod
    def model_name(self) -> str:
        """AROME or ARPEGE"""
        pass

    @property
    @abstractmethod
    def run_frequency(self) -> int:
        """Frequency at which model is updated."""
        pass

    @property
    @abstractmethod
    def entry_point(self) -> str:
        """Entry point to AROME/ARPEGE service."""
        pass

    @property
    @abstractmethod
    def indicators(self) -> str:
        """The list of available indicators"""
        pass

    @property
    @abstractmethod
    def instant_indicators(self) -> str:
        """The list of instant indicators"""
        pass

    def _get_capabilities(self) -> dict:
        """The Capabilities of the AROME/ARPEGE service."""

        url = f"{self.base_url}/{self.entry_point}/GetCapabilities"
        params = {
            "service": "WCS",
            "version": "2.0.1",
            "language": "eng",
        }
        try:
            response = self._get_request(url, params=params)
        except MissingDataError as e:
            logger.error(f"Error fetching the capabilities: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Params: {params}")
            raise e

        xml = response.text

        try:
            return xmltodict.parse(xml)
        except MissingDataError as e:
            logger.error(f"Error parsing the XML response: {e}")
            logger.error(f"Response: {xml}")
            raise e

    @abstractmethod
    def _validate_parameters(self):
        """Assert parameters are valid."""
        pass

    def _get_coverage_description(self, coverage_id: str) -> dict:
        """Get the description of a coverage.

        .. warning::
            The return value is the raw XML data.
            Not yet parsed to be usable.
            In the future, it should be possible to use it to
            get the available heights, times, latitudes and longitudes of the forecast.

        Parameters
        ----------
        coverage_id: str
            the Coverage ID. Use :meth:`get_coverage` to access the available coverage ids.
            By default use the latest temperature coverage ID.

        Returns
        -------
        description : dict
            the description of the coverage.
        """
        url = f"{self.base_url}/{self.entry_point}/DescribeCoverage"
        params = {
            "service": "WCS",
            "version": "2.0.1",
            "coverageid": coverage_id,
        }
        response = self._get_request(url, params=params)
        return xmltodict.parse(response.text)

    def _transform_grib_to_df(self) -> pd.DataFrame:
        "Transform grib file into pandas dataframe"

        ds = xr.open_dataset(self.filepath, engine="cfgrib")
        df = ds.to_dataframe().reset_index()
        os.remove(str(self.filepath))
        idx_files = glob.glob(f"{self.filepath}.*.idx")
        for idx_file in idx_files:
            os.remove(idx_file)

        return df

    def _get_data_single_forecast(
        self,
        coverage_id: str,
        forecast_horizon: int,
        pressure: int | None,
        height: int | None,
        lat: tuple,
        long: tuple,
    ) -> pd.DataFrame:
        """Returns the forecasts for a given time and indicator.

        Args:
            coverage_id (str): the indicator.
            height (int): height in meters
            pressure (int): pressure in hPa
            forecast_horizon (int): the forecast horizon in hours (how many hours ahead)
            lat (tuple): minimum and maximum latitude
            long (tuple): minimum and maximum longitude

        Returns:
            pd.DataFrame: The forecast for the specified time.
        """

        self._get_coverage_file(
            coverage_id=coverage_id,
            height=height,
            pressure=pressure,
            forecast_horizon_in_seconds=forecast_horizon * 3600,
            lat=lat,
            long=long,
        )

        df = self._transform_grib_to_df()

        df.drop(columns=["surface", "valid_time"], errors="ignore", inplace=True)
        df.rename(
            columns={
                "time": "run",
                "heightAboveGround": "height",
                "isobaricInhPa": "pressure",
                "step": "forecast_horizon",
            },
            inplace=True,
        )

        if self.folderpath is not None:
            shutil.rmtree(self.folderpath)

        return df

    def _get_coverage_file(
        self,
        coverage_id: str,
        height: int | None = None,
        pressure: int | None = None,
        forecast_horizon_in_seconds: int = 0,
        lat: tuple = (37.5, 55.4),
        long: tuple = (-12, 16),
        file_format: str = "grib",
        filepath: Path | None = None,
    ) -> Path:
        """Fetch the raster values of the model predictions.

        The raster is saved to a file in the cache directory.

        Parameters
        ----------
        coverage_id: str
            The ID of the coverage to fetch. Use the `get_coverage` method to find available coverage IDs.
            By default, it uses the latest temperature coverage ID.
        height: int, optional
            The height in meters for the model. Defaults to 2 meters above ground.
            The available heights can be accessed from the API, but this feature is not implemented yet.
        forecast_horizon_in_seconds: int, optional
            The forecast horizon in seconds into the future. Defaults to 0s (current time).
            The available forecast horizons can be known via :meth:`get_coverage_description`
        lat: tuple[float], optional
            The minimum and maximum latitudes to return. Defaults to the latitudes of France.
        long: tuple[float], optional
            The minimum and maximum longitudes to return. Defaults to the longitudes of France.
        file_format: str, optional
            The format of the file to save the raster data. Defaults to "grib".
        filepath: Path, optional
            The path where the file will be saved. If not provided, it will be saved in the cache directory.

        Returns
        -------
        filename : pathlib.Path
            The path to the file containing the raster data in the specified format.

        .. see-also::
        :func:`.raster.plot_tiff_file` to plot the file.
        """
        self.filepath = filepath

        file_extension = "tiff" if file_format == "tiff" else "grib"

        filename = (
            f"{height or '_'}m_{forecast_horizon_in_seconds}Z_{lat[0]}-{lat[1]}_{long[0]}-{long[1]}.{file_extension}"
        )

        if self.filepath is None:
            current_working_directory = Path(os.getcwd())
            self.filepath = current_working_directory / coverage_id / filename
            self.folderpath = current_working_directory / coverage_id
            logger.debug(f"{self.filepath}")
            logger.debug("File not found in Cache, fetching data")
            url = f"{self.base_url}/{self.entry_point}/GetCoverage"
            params = {
                "service": "WCS",
                "version": "2.0.1",
                "coverageid": coverage_id,
                "format": "application/wmo-grib",
                "subset": [
                    *([f"pressure({pressure})"] if pressure is not None else []),
                    *([f"height({height})"] if height is not None else []),
                    f"time({forecast_horizon_in_seconds})",
                    f"lat({lat[0]},{lat[1]})",
                    f"long({long[0]},{long[1]})",
                ],
            }
            response = self._get_request(url, params=params)

            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "wb") as f:
                f.write(response.content)

        return self.filepath
