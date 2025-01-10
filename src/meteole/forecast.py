from __future__ import annotations

import datetime as dt
import logging
import re
import tempfile
from abc import ABC, abstractmethod
from functools import reduce
from typing import Any
from warnings import warn

import pandas as pd
import xarray as xr
import xmltodict

from meteole.clients import BaseClient
from meteole.errors import MissingDataError

logger = logging.getLogger(__name__)


class WeatherForecast(ABC):
    """(Abstract)
    Base class for weather forecast models.

    Note: Currently, this class is highly related to Meteo-France models.
    This will not be the case in the future.

    Attributes:
        territory: Covered area (e.g., FRANCE, ANTIL, ...).
        precision: Precision value of the forecast.
        capabilities: DataFrame containing details on all available coverage ids.
    """

    # Class constants
    # Global
    API_VERSION: str = "1.0"
    PRECISION_FLOAT_TO_STR: dict[float, str] = {0.25: "025", 0.1: "01", 0.05: "005", 0.01: "001", 0.025: "0025"}
    FRANCE_METRO_LONGITUDES = (-5.1413, 9.5602)
    FRANCE_METRO_LATITUDES = (41.33356, 51.0889)

    # Model
    MODEL_NAME: str = "Defined in subclass"
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
        """Initialize attributes.

        Args:
            territory: The ARPEGE territory to fetch.
            api_key: The API key for authentication. Defaults to None.
            token: The API token for authentication. Defaults to None.
            application_id: The Application ID for authentication. Defaults to None.
        """
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
        """Getter method of the capabilities attribute.

        Returns:
            DataFrame of details on all available coverage ids.
        """
        if self._capabilities is None:
            self._capabilities = self._build_capabilities()
        return self._capabilities

    @property
    def indicators(self) -> list[str]:
        """Getter method of the indicators.

        Indicators are identifying the kind of a predicted value (i.e., measurement).

        Warning: This method is deprecated as INDICATORS is now a class constant.

        Returns:
            List of covered indicators.
        """
        warn(
            "The 'indicators' attribute is deprecated, it will be removed soon. "
            "Use 'INDICATORS' instead (class constant).",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.INDICATORS

    @abstractmethod
    def _validate_parameters(self) -> None:
        """Check the territory and the precision parameters.

        Raise:
            ValueError: At least, one parameter is not good.
        """
        raise NotImplementedError

    def get_capabilities(self) -> pd.DataFrame:
        """Explicit "getter method" of the capabilities attribute.

        Returns:
            DataFrame of details on all available coverage ids.
        """
        return self.capabilities

    def get_coverage_description(self, coverage_id: str) -> dict[str, Any]:
        """Return the available axis (times, heights) of a coverage.

        TODO: Other informations can be fetched, not yet implemented.

        Args:
            coverage_id: An id of a coverage, use get_capabilities() to get them.

        Returns:
            A dictionary containing more info on the coverage.
        """
        description = self._get_coverage_description(coverage_id)
        grid_axis = description["wcs:CoverageDescriptions"]["wcs:CoverageDescription"]["gml:domainSet"][
            "gmlrgrid:ReferenceableGridByVectors"
        ]["gmlrgrid:generalGridAxis"]

        return {
            "forecast_horizons": [int(time / 3600) for time in self._get_available_feature(grid_axis, "time")],
            "heights": self._get_available_feature(grid_axis, "height"),
            "pressures": self._get_available_feature(grid_axis, "pressure"),
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
        """Return the coverage data (i.e., the weather forecast data).

        Args:
            indicator: Indicator of a coverage to retrieve.
            lat: Minimum and maximum latitude.
            long: Minimum and maximum longitude.
            heights: Heights in meters.
            pressures: Pressures in hPa.
            forecast_horizons: List of integers, representing the forecast horizons in hours.
            run: The model inference timestamp. If None, defaults to the latest available run.
                Expected format: "YYYY-MM-DDTHH:MM:SSZ".
            interval: The aggregation period. Must be None for instant indicators;
                    raises an error if specified. Defaults to "P1D" for time-aggregated indicators such
                    as TOTAL_PRECIPITATION.
            coverage_id: An id of a coverage, use get_capabilities() to get them.

        Returns:
            pd.DataFrame: The complete run for the specified execution.
        """
        # Ensure we only have one of coverage_id, indicator
        if not bool(indicator) ^ bool(coverage_id):
            raise ValueError("Argument `indicator` or `coverage_id` need to be set (only one of them)")

        if indicator is not None:
            coverage_id = self._get_coverage_id(indicator, run, interval)

        logger.info(f"Using `coverage_id={coverage_id}`")

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

    def _build_capabilities(self) -> pd.DataFrame:
        """(Protected)
        Fetch and build the model capabilities.

        Returns:
            DataFrame all the details.
        """

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
        """(Protected)
        Retrieve a `coverage_id` from the capabilities based on the provided parameters.

        Args:
            indicator: The indicator to retrieve. This parameter is required.
            run: The model inference timestamp. If None, defaults to the latest available run.
                Expected format: "YYYY-MM-DDTHH:MM:SSZ". Defaults to None.
            interval: The aggregation period. Must be None for instant indicators;
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
            if not interval:
                # no interval is expected for instant indicators
                pass
            else:
                raise ValueError(
                    f"interval={interval} is invalid. No interval is expected (=set to None) for instant "
                    "indicator `{indicator}`."
                )
        else:
            if not interval:
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

        if interval:
            coverage_id += f"_{interval}"

        return coverage_id

    def _raise_if_invalid_or_fetch_default(
        self, param_name: str, inputs: list[int] | None, availables: list[int]
    ) -> list[int]:
        """(Protected)
        Checks validity of `inputs`.

        Checks if the elements in `inputs` are in `availables` and raises a ValueError if not.
        If `inputs` is empty or None, uses the first element from `availables` as the default value.

        Args:
            param_name (str): The name of the parameter to validate.
            inputs (list[int] | None): The list of inputs to validate.
            availables (list[int]): The list of available values.

        Returns:
            list[int]: The validated list of inputs or the default value.

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

    def _fetch_capabilities(self) -> dict[Any, Any]:
        """Fetch the model capabilities.

        Returns:
            Raw capabilities (dictionary).
        """

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

    def _get_coverage_description(self, coverage_id: str) -> dict[Any, Any]:
        """(Protected)
        Get the description of a coverage.

        Warning:
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

    def _grib_bytes_to_df(self, grib_str: bytes) -> pd.DataFrame:
        """(Protected)
        Converts GRIB data (in binary format) into a pandas DataFrame.

        This method writes the binary GRIB data to a temporary file, reads it using
        the `cfgrib` engine via xarray, and converts the resulting xarray Dataset
        into a pandas DataFrame.

        Args:
            grib_str (bytes): Binary GRIB data as a byte string.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the extracted GRIB data,
            with columns like `time`, `latitude`, `longitude`, and any associated
            variables from the GRIB file.

        Raises:
            ValueError: If the input `grib_str` is not of type `bytes` or `bytearray`.

        Notes:
            - The method requires the `cfgrib` engine to be installed.
            - The temporary file used for parsing is automatically deleted after use.
            - Ensure the input GRIB data is valid and encoded in a binary format.
        """

        with tempfile.NamedTemporaryFile() as temp_file:
            # Write the GRIB binary data to the temporary file
            temp_file.write(grib_str)
            temp_file.flush()  # Ensure the data is written to disk

            # Open the GRIB file as an xarray Dataset using the cfgrib engine
            ds = xr.open_dataset(temp_file.name, engine="cfgrib")

            # Convert the Dataset to a pandas DataFrame
            df = ds.to_dataframe().reset_index()

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
        """(Protected)
        Return the forecast's data for a given time and indicator.

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

        grib_binary: bytes = self._get_coverage_file(
            coverage_id=coverage_id,
            height=height,
            pressure=pressure,
            forecast_horizon_in_seconds=forecast_horizon * 3600,
            lat=lat,
            long=long,
        )

        df: pd.DataFrame = self._grib_bytes_to_df(grib_binary)

        # Drop and rename columns
        df.drop(columns=["surface", "valid_time"], errors="ignore", inplace=True)
        df.rename(
            columns={
                "time": "run",
                "step": "forecast_horizon",
            },
            inplace=True,
        )
        known_columns = {"latitude", "longitude", "run", "forecast_horizon", "heightAboveGround", "isobaricInhPa"}
        indicator_column = (set(df.columns) - known_columns).pop()

        if indicator_column == "unknown":
            base_name = "".join([word[0] for word in coverage_id.split("__")[0].split("_")]).lower()
        else:
            base_name = re.sub(r"\d.*", "", indicator_column)

        if "heightAboveGround" in df.columns:
            suffix = f"_{int(df['heightAboveGround'].iloc[0])}m"
        elif "isobaricInhPa" in df.columns:
            suffix = f"_{int(df['isobaricInhPa'].iloc[0])}hpa"
        else:
            suffix = ""

        new_indicator_column = f"{base_name}{suffix}"
        df.rename(columns={indicator_column: new_indicator_column}, inplace=True)

        df.drop(
            columns=["isobaricInhPa", "heightAboveGround", "meanSea", "potentialVorticity"],
            errors="ignore",
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
    ) -> bytes:
        """(Protected)
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

        return response.content

    @staticmethod
    def _get_available_feature(grid_axis: list[dict[str, Any]], feature_name: str) -> list[int]:
        """(Protected)
        Retrieve available features.

        TODO: add more details here.

        Args:
            grid_axis: ?
            feature_name: ?

        Returns:
            List of available feature.
        """
        feature_grid_axis: list[dict[str, Any]] = [
            ax for ax in grid_axis if str(ax["gmlrgrid:GeneralGridAxis"]["gmlrgrid:gridAxesSpanned"]) == feature_name
        ]

        features: list[int] = (
            list(map(int, feature_grid_axis[0]["gmlrgrid:GeneralGridAxis"]["gmlrgrid:coefficients"].split(" ")))
            if len(feature_grid_axis) > 0
            else []
        )
        return features

    def get_combined_coverage(
        self,
        indicator_names: list[str],
        runs: list[str | None] | None = None,
        heights: list[int] | None = None,
        pressures: list[int] | None = None,
        intervals: list[str | None] | None = None,
        lat: tuple = FRANCE_METRO_LATITUDES,
        long: tuple = FRANCE_METRO_LONGITUDES,
        forecast_horizons: list[int] | None = None,
    ) -> pd.DataFrame:
        """
        Get a combined DataFrame of coverage data for multiple indicators and different runs.

        This method retrieves and aggregates coverage data for specified indicators, with options
        to filter by height, pressure, and forecast_horizon. It returns a concatenated DataFrame
        containing the coverage data for all provided runs.

        Args:
            indicator_names (list[str]): A list of indicator names to retrieve data for.
            runs (list[str]): A list of runs for each indicator. Format should be "YYYY-MM-DDTHH:MM:SSZ".
            heights (list[int] | None): A list of heights in meters to filter by (default is None).
            pressures (list[int] | None): A list of pressures in hPa to filter by (default is None).
            intervals (list[str] | None): A list of aggregation periods (default is None).
                    Must be `None` or "" for instant indicators ; otherwise, raises an exception.
                    Defaults to 'P1D' for time-aggregated indicators.
            lat (tuple): The latitude range as (min_latitude, max_latitude). Defaults to FRANCE_METRO_LATITUDES.
            long (tuple): The longitude range as (min_longitude, max_longitude). Defaults to FRANCE_METRO_LONGITUDES.
            forecast_horizons (list[int] | None): A list of forecast horizon values in hours. Defaults to None.

        Returns:
            pd.DataFrame: A combined DataFrame containing coverage data for all specified runs and indicators.

        Raises:
            ValueError: If the length of `heights` does not match the length of `indicator_names`.
        """
        if runs is None:
            runs = [None]
        coverages = [
            self._get_combined_coverage_for_single_run(
                indicator_names=indicator_names,
                run=run,
                lat=lat,
                long=long,
                heights=heights,
                pressures=pressures,
                intervals=intervals,
                forecast_horizons=forecast_horizons,
            )
            for run in runs
        ]
        return pd.concat(coverages, axis=0).reset_index(drop=True)

    def _get_combined_coverage_for_single_run(
        self,
        indicator_names: list[str],
        run: str | None = None,
        heights: list[int] | None = None,
        pressures: list[int] | None = None,
        intervals: list[str | None] | None = None,
        lat: tuple = FRANCE_METRO_LATITUDES,
        long: tuple = FRANCE_METRO_LONGITUDES,
        forecast_horizons: list[int] | None = None,
    ) -> pd.DataFrame:
        """(Protected)
        Get a combined DataFrame of coverage data for a given run considering a list of indicators.

        This method retrieves and aggregates coverage data for specified indicators, with options
        to filter by height, pressure, and forecast_horizon. It returns a concatenated DataFrame
        containing the coverage data.

        Args:
            indicator_names (list[str]): A list of indicator names to retrieve data for.
            run (str): A single runs for each indicator. Format should be "YYYY-MM-DDTHH:MM:SSZ".
            heights (list[int] | None): A list of heights in meters to filter by (default is None).
            pressures (list[int] | None): A list of pressures in hPa to filter by (default is None).
            intervals (Optional[list[str]]): A list of aggregation periods (default is None).
                    Must be `None` or "" for instant indicators ; otherwise, raises an exception.
                    Defaults to 'P1D' for time-aggregated indicators.
            lat (tuple): The latitude range as (min_latitude, max_latitude). Defaults to FRANCE_METRO_LATITUDES.
            long (tuple): The longitude range as (min_longitude, max_longitude). Defaults to FRANCE_METRO_LONGITUDES.
            forecast_horizons (list[int] | None): A list of forecast horizon values in hours. Defaults to None.

        Returns:
            pd.DataFrame: A combined DataFrame containing coverage data for all specified runs and indicators.

        Raises:
            ValueError: If the length of `heights` does not match the length of `indicator_names`.
        """

        def _check_params_length(params: list[Any] | None, arg_name: str) -> list[Any]:
            """(Protected)
            Assert length is ok or raise an error.

            Args:
                params: list of parameters.
                arg_name: argument name.

            Returns:
                The given parameters unchanged.

            Raises:
                ValueError: The length of {arg_name} must match the length of indicator_names.
            """
            if params is None:
                return [None] * len(indicator_names)
            if len(params) != len(indicator_names):
                raise ValueError(
                    f"The length of {arg_name} must match the length of indicator_names."
                    f" If you want multiple {arg_name} for a single indicator, create multiple"
                    " entries in `indicator_names`."
                )
            return params

        heights = _check_params_length(heights, "heights")
        pressures = _check_params_length(pressures, "pressures")
        intervals = _check_params_length(intervals, "intervals")

        # Get coverage id from run and indicator_name
        coverage_ids = [
            self._get_coverage_id(indicator_name, run, interval)
            for indicator_name, interval in zip(indicator_names, intervals)
        ]

        if forecast_horizons:
            # Check forecast_horizons is valid for all indicators
            invalid_coverage_ids = self._validate_forecast_horizons(coverage_ids, forecast_horizons)
            if invalid_coverage_ids:
                raise ValueError(f"{forecast_horizons} are not valid for these coverage_ids : {invalid_coverage_ids}")
        else:
            forecast_horizons = [self.find_common_forecast_horizons(coverage_ids)[0]]
            logger.info(f"Using common forecast_horizons `forecast_horizons={forecast_horizons}`.")

        coverages = [
            self.get_coverage(
                coverage_id=coverage_id,
                run=run,
                lat=lat,
                long=long,
                heights=[height] if height is not None else [],
                pressures=[pressure] if pressure is not None else [],
                forecast_horizons=forecast_horizons,
            )
            for coverage_id, height, pressure in zip(coverage_ids, heights, pressures)
        ]

        return reduce(
            lambda left, right: pd.merge(
                left,
                right,
                on=["latitude", "longitude", "run", "forecast_horizon"],
                how="inner",
                validate="one_to_one",
            ),
            coverages,
        )

    def _get_forecast_horizons(self, coverage_ids: list[str]) -> list[list[int]]:
        """(Protected)
        Retrieve the times for each coverage_id.

        Args:
            coverage_ids: List of coverage IDs.

        Returns:
            List of times for each coverage ID.
        """
        indicator_times: list[list[int]] = []
        for coverage_id in coverage_ids:
            times = self.get_coverage_description(coverage_id)["forecast_horizons"]
            indicator_times.append(times)
        return indicator_times

    def find_common_forecast_horizons(
        self,
        list_coverage_id: list[str],
    ) -> list[int]:
        """Find common forecast_horizons among coverage IDs.

        Args:
            indicator_names: List of indicator names.
            run: Identifies the model inference. Defaults to latest if None. Format "YYYY-MM-DDTHH:MM:SSZ".
            intervals: List of aggregation periods. Must be None for instant indicators, otherwise raises.
                    Defaults to P1D for time-aggregated indicators like TOTAL_PRECIPITATION.

        Returns:
            List of common forecast_horizons.
        """
        indicator_forecast_horizons = self._get_forecast_horizons(list_coverage_id)

        common_forecast_horizons = indicator_forecast_horizons[0]
        for times in indicator_forecast_horizons[1:]:
            common_forecast_horizons = [time for time in common_forecast_horizons if time in times]

        all_times = []
        for times in indicator_forecast_horizons:
            all_times.extend(times)

        return sorted(common_forecast_horizons)

    def _validate_forecast_horizons(self, coverage_ids: list[str], forecast_horizons: list[int]) -> list[str]:
        """(Protected)
        Validate forecast_horizons for a list of coverage IDs.

        Args:
            coverage_ids: List of coverage IDs.
            forecast_horizons: List of time forecasts to validate.

        Returns:
            List of invalid coverage IDs.
        """
        indicator_forecast_horizons = self._get_forecast_horizons(coverage_ids)

        invalid_coverage_ids = [
            coverage_id
            for coverage_id, times in zip(coverage_ids, indicator_forecast_horizons)
            if not set(forecast_horizons).issubset(times)
        ]

        return invalid_coverage_ids
