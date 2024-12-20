import datetime as dt
import glob
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd
import xarray as xr
import xmltodict

from meteole.clients import BaseClient
from meteole.errors import MissingDataError

logger = logging.getLogger(__name__)


class Forecast(ABC):
    """(Abstract class)
    Provides a unified interface to query AROME and ARPEGE endpoints

    Attributes
    ----------
    capabilities: pandas.DataFrame
        coverage dataframe containing the details of all available coverage_ids
    """

    # Class constants
    # Global
    API_VERSION: str = "1.0"
    PRECISION_FLOAT_TO_STR: dict[float, str] = {0.25: "025", 0.1: "01", 0.05: "005", 0.01: "001", 0.025: "0025"}
    FRANCE_METRO_LONGITUDES = (-5.1413, 9.5602)
    FRANCE_METRO_LATITUDES = (41.33356, 51.0889)

    # Model
    MODEL_NAME: str = "Defined in subclass"
    RUN_FREQUENCY: int = 0
    BASE_ENTRY_POINT: str = "Defined in subclass"
    INDICATORS: list[str] = []
    INSTANT_INDICATORS: list[str] = []
    DEFAULT_TERRITORY: str = "FRANCE"
    DEFAULT_PRECISION: float = 0.01
    CLIENT_CLASS: type[BaseClient]

    def __init__(
        self,
        client: BaseClient | None = None,
        *,
        territory: str = DEFAULT_TERRITORY,
        precision: float = DEFAULT_PRECISION,
        **kwargs: Any,
    ):
        """Init the Forecast object."""
        self.territory = territory  # "FRANCE", "ANTIL", or others (see API doc)
        self.precision = precision
        self._validate_parameters()

        self._capabilities: pd.DataFrame | None = None
        self._entry_point: str = (
            f"{self.BASE_ENTRY_POINT}-{self.PRECISION_FLOAT_TO_STR[self.precision]}-{self.territory}-WCS"
        )
        self._model_base_path = self.MODEL_NAME + "/" + self.API_VERSION

        if client is not None:
            self._client = client
        else:
            # Try to instantiate it (can be user friendly)
            self._client = self.CLIENT_CLASS(**kwargs)

    @property
    def capabilities(self) -> pd.DataFrame:
        """TODO"""
        if self._capabilities is None:
            self._capabilities = self._build_capabilities()
        return self._capabilities

    @property
    def indicators(self) -> pd.DataFrame:
        """TODO"""
        return self.INDICATORS

    @abstractmethod
    def _validate_parameters(self):
        """Assert parameters are valid."""
        pass

    def get_capabilities(self) -> pd.DataFrame:
        "Returns the coverage dataframe containing the details of all available coverage_ids"
        return self.capabilities

    def get_coverage_description(self, coverage_id: str) -> dict:
        """This endpoint returns the available axis (times, heights) to properly query coverage

        TODO: other informations can be fetched from this endpoint, not yet implemented.

        Args:
            coverage_id (str): use :meth:`get_capabilities()` to list all available coverage_id
        """

        # Get coverage description
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

    def get_coverage(
        self,
        indicator: str | None = None,
        lat: tuple = FRANCE_METRO_LATITUDES,
        long: tuple = FRANCE_METRO_LONGITUDES,
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

    def get_coverages(
        self,
        coverage_ids: list[str],
        lat: tuple = FRANCE_METRO_LATITUDES,
        long: tuple = FRANCE_METRO_LONGITUDES,
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

    def _build_capabilities(self) -> pd.DataFrame:
        "Returns the coverage dataframe containing the details of all available coverage_ids"

        logger.info("Fetching all available coverages...")

        capabilities = self._fetch_capabilities()
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

    def _get_coverage_id(
        self,
        indicator: str,
        run: str | None = None,
        interval: str | None = None,
    ) -> str:
        """
        Retrieves a `coverage_id` from the capabilities based on the provided parameters.

        Args:
            indicator (str): The indicator to retrieve. This parameter is required.
            run (str | None, optional): The model inference timestamp. If None, defaults to the latest available run.
                Expected format: "YYYY-MM-DDTHH:MM:SSZ". Defaults to None.
            interval (str | None, optional): The aggregation period. Must be None for instant indicators;
                raises an error if specified. Defaults to "P1D" for time-aggregated indicators such as
                TOTAL_PRECIPITATION.

        Returns:
            str: The `coverage_id` corresponding to the given parameters.

        Raises:
            ValueError: If `indicator` is missing or invalid.
            ValueError: If `interval` is invalid or required but missing.
        """
        capabilities = self.capabilities[self.capabilities["indicator"] == indicator]

        if indicator not in self.INDICATORS:
            raise ValueError(f"Unknown `indicator` - checkout `{self.MODEL_NAME}.indicators` to have the full list.")

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

        if indicator in self.INSTANT_INDICATORS:
            if interval is None:
                # no interval is expected for instant indicators
                pass
            else:
                raise ValueError(
                    f"interval={interval} is invalid. No interval is expected (=set to None) for instant "
                    "indicator `{indicator}`."
                )
        else:
            if interval is None:
                interval = "P1D"
                logger.info(
                    f"`interval=None` is invalid  for non-instant indicators. Using default `interval={interval}`"
                )
            elif interval not in valid_intervals:
                raise ValueError(
                    f"interval={interval} is invalid  for non-instant indicators. `{indicator}`."
                    f" Use valid intervals: {valid_intervals}"
                )

        coverage_id = f"{indicator}___{run}"

        if interval is not None:
            coverage_id += f"_{interval}"

        return coverage_id

    def _raise_if_invalid_or_fetch_default(
        self, param_name: str, inputs: list[int] | None, availables: list[int]
    ) -> list[int]:
        """Checks validity of `inputs`.

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

    def _fetch_capabilities(self) -> dict:
        """The Capabilities of the AROME/ARPEGE service."""

        url = f"{self._model_base_path}/{self._entry_point}/GetCapabilities"
        params = {
            "service": "WCS",
            "version": "2.0.1",
            "language": "eng",
        }
        try:
            response = self._client.get(url, params=params)
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

    def _get_coverage_description(self, coverage_id: str) -> dict:
        """Get the description of a coverage.

        .. warning::
            The return value is the raw XML data.
            Not yet parsed to be usable.
            In the future, it should be possible to use it to
            get the available heights, times, latitudes and longitudes of the forecast.

        Args:
            coverage_id (str): the Coverage ID. Use :meth:`get_coverage` to access the available coverage ids.
                By default use the latest temperature coverage ID.

        Returns:
            description (dict): the description of the coverage.
        """
        url = f"{self._model_base_path}/{self._entry_point}/DescribeCoverage"
        params = {
            "service": "WCS",
            "version": "2.0.1",
            "coverageid": coverage_id,
        }
        response = self._client.get(url, params=params)
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
        """
        Retrieves raster data for a specified model prediction and saves it to a file.

        If no `filepath` is provided, the file is saved to a default cache directory under
        the current working directory.

        Args:
            coverage_id (str): The coverage ID to retrieve. Use `get_coverage` to list available coverage IDs.
            height (int, optional): The height above ground level in meters. Defaults to 2 meters.
                If not provided, no height subset is applied.
            pressure (int, optional): The pressure level in hPa. If not provided, no pressure subset is applied.
            forecast_horizon_in_seconds (int, optional): The forecast horizon in seconds into the future.
                Defaults to 0 (current time).
            lat (tuple[float, float], optional): Tuple specifying the minimum and maximum latitudes.
                Defaults to (37.5, 55.4), covering the latitudes of France.
            long (tuple[float, float], optional): Tuple specifying the minimum and maximum longitudes.
                Defaults to (-12, 16), covering the longitudes of France.
            file_format (str, optional): The format of the raster file. Supported formats are "grib" and "tiff".
                Defaults to "grib".
            filepath (Path, optional): The file path where the raster file will be saved. If not specified,
                the file is saved to a cache directory.

        Returns:
            Path: The file path to the saved raster data.

        Notes:
            - If the file does not exist in the cache, it will be fetched from the API and saved.
            - Supported subsets include pressure, height, time, latitude, and longitude.

        See Also:
            raster.plot_tiff_file: Method for plotting raster data stored in TIFF format.
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
            url = f"{self._model_base_path}/{self._entry_point}/GetCoverage"
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
            response = self._client.get(url, params=params)

            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "wb") as f:
                f.write(response.content)

        return self.filepath

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
