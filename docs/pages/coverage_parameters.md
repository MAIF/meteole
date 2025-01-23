Weather forecasts from Météo-France APIs are based on key parameters that vary from indicator to indicator, which makes them complex to use.

Understanding coverages is a must to have a comprehensive usage of Météo-France forecasting models like AROME, AROME INSTANTANÉ or ARPEGE.

## Coverage_id

### Introduction
A coverage_id looks like that:

> WIND_SPEED__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND___2024-01-16T09.00.00Z

It contains several information in a single string:

- WIND_SPEED: Indicates that the data pertains to wind speed.
- SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND: Specifies that the measurement is taken at a particular height above the ground.
- 2024-01-16T09.00.00Z: Represents the date and time of the measurement, in ISO 8601 format (January 16, 2024, at 09:00 UTC).

if you want to display all valid coverage_ids, you can use `get_capabilities`:

```python
from meteole import AromeForecast

arome = AromeForecast(application_id=application_id)

arome.get_capabilities()
```

### Time-series coverages

Some coverages can contain an additional suffix named `interval`:

> TEMPERATURE__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND___2024-01-16T09.00.00Z_PT1H

`PT1H` Specifies the interval, meaning the data is provided at 1-hour intervals.

When no interval is specified, it means coverage returns a single datapoint instead of a timeseries.

## Others parameters
### Forecast_horizons
The time of day to which the prediction corresponds must be specified. For example, for a run of 12:00, in 1 hour's time, we have the weather indicator prediction of 13:00.
The `get_coverage method` takes as (optional) parameter the list of desired forecast hours (in `dt.timedelta` format), named `forecast_horizons`.

To get the list of available `forecast_horizons`, use the function `get_coverage_description` as described in the example below.

```python
from meteole import arome

arome_client = arome.AromeForecast(application_id=APPLICATION_ID)

# Create coverage_id
capabilities = arome_client.get_capabilities()
indicator = 'V_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND'
coverage_id = capabilities[capabilities['indicator'] == indicator]['id'].iloc[0]

# get the description of the coverage
coverage_axis = arome.get_coverage_description(coverage_id)

# retrieve the available forecast_horizons
coverage_axis['forecast_horizons']
```

### Heights and Pressures

Atmospheric parameters can be measured at various heights and pressure levels, providing comprehensive data for weather analysis and forecasting. In consequence, some coverages must be queried with a `height` or `pressure` parameter.

To get the list of available `height` or `pressure` parameters, use the function `get_coverage_description` like `forecast_horizons`.

```python
coverage_axis['heights']
coverage_axis['pressures']
```

### Geographical Coverage
The geographical coverage of forecasts can be customized using the `lat` and `long` parameters. By default, Meteole retrieves data for the entire metropolitan France.
