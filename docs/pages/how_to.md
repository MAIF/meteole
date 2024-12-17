## Installation

Ensure that you have correctly installed **Meteole** before (check [Installation page](installation.md) for details)

```python
pip install meteole
```

## Get a token, an API key or an application ID

1. Create an account on [the Météo-France API portal](https://portail-api.meteofrance.fr/).
2. Subscribe to the desired services (Arome, Arpege, etc.).
3. Retrieve the API token (or key) by going to “Mes APIs” and then Générer token”.

> 💡
> 
> Using an APPLICATION_ID allows for token auto-refresh. It avoids re-generating a token or an API key when it is expired.
>
> Find your APPLICATION_ID in your [API dashboard](https://portail-api.meteofrance.fr/web/fr/dashboard) > "Générer Token". 
> 
> Then checkout the `curl` field at the bottom of the page that looks like that: 
> ```bash 
> curl -k -X POST https://portail-api.meteofrance.fr/token -d "grant_type=client_credentials" -H "Authorization: Basic ktDvFBDP8w6jGfKuK4yB1nS6oLOK4bfoFwEqmANOIvNMF8vG6B51tgJeZQcOO1d3qYyK"
> ```
>
> The string that comes rights after "Basic" is your APPLICATION_ID (`ktDvFBDP8w6jGfKuK4yB1nS6oLOK4bfoFwEqmANOIvNMF8vG6B51tgJeZQcOO1d3qYyK` in this example)

## Get the latest vigilance bulletin

Meteo France offers a vigilance bulletin that provides nationwide predictions of potential weather risks.

For data usage, access the predicted phenomena to trigger modeling based on the forecasts.

```python
from meteole import Vigilance

# application_id: obtain it on the Météo-France API portal
client = Vigilance(application_id=APPLICATION_ID) 

df_phenomenon, df_timelaps = client.get_phenomenon() 

# Fetch vigilance bulletins
textes_vigilance = client.get_vigilance_bulletin() 

# Display the vigilance vignette
client.get_vignette() 
```

![bulletin vigilance](./assets/img/png/vignette_exemple.png)

> More details about Vigilance Bulletin in [the official Meteo France Documentation](https://donneespubliques.meteofrance.fr/?fond=produit&id_produit=305&id_rubrique=50)

## Get AROME or ARPEGE data

The flagship weather forecasting models of Météo-France are accessible via the Météo-France APIs.

| Characteristics  | AROME                | ARPEGE               |
|------------------|----------------------|----------------------|
| Resolution       | 1.3 km               | 10 km                |
| Update Frequency | Every 3 hours        | Every 6 hours        |
| Forecast Range   | Up to 51 hours       | Up to 114 hours      |

```python
from meteole import arome

arome_client = arome.AromeForecast(application_id=APPLICATION_ID)  # api_key found on portail.meteo-france.Fr

# get all available coverages
# coverage: a string containing indicator + run
capabilities = arome_client.get_capabilities()

# fetch a valid coverage_id for WIND_GUST
indicator = 'V_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND'
coverage_id = capabilities[capabilities['indicator'] == indicator]['id'].iloc[0]

# get the data 
# (params heights and forecast_horizons default to their first allowed value)
df_arome = arome_client.get_coverage(coverage_id)  
```

## Advanced guide: coverages

### Introduction

Understanding coverages is a must to have a comprehensive usage of Météo-France forecasting models like AROME or ARPEGE.

A coverageid looks like that:

> WIND_SPEED__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND___2024-01-16T09.00.00Z

It contains several information in a single string:

- WIND_SPEED: Indicates that the data pertains to wind speed.
- SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND: Specifies that the measurement is taken at a particular height above the ground.
- 2024-01-16T09.00.00Z: Represents the date and time of the measurement, in ISO 8601 format (January 16, 2024, at 09:00 UTC).

### Time-series coverages

Some coverages can contain an additional suffix:

> TEMPERATURE__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND___2024-01-16T09.00.00Z_PT1H

`PT1H` Specifies the interval, meaning the data is provided at 1-hour intervals. 

When no interval is specified, it means coverage returns a single datapoint instead of a timeseries.

### Height

Atmospheric parameters can be measured at various heights and pressure levels, providing comprehensive data for weather analysis and forecasting. In consequence, some coverages must be queried with a `height` parameter.

To get the list of available `height` parameters, use the function `get_coverage_description` as described in the example below.

```python
from meteole import arome

arome_client = arome.AromeForecast(application_id=APPLICATION_ID)  # api_key found on portail.meteo-france.Fr

# get all available coverage ids with `get_capabilities`
capabilities = arome_client.get_capabilities()

# fetch a valid coverage_id for WIND_GUST
indicator = 'V_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND'
coverage_id = capabilities[capabilities['indicator'] == indicator]['id'].iloc[0]

# get the description of the coverage
coverage_axis = arome.get_coverage_description(random_coverage_id)

# retrieve the available heights 
coverage_axis['heights']
```

Similarly, the AROME and ARPEGE can have different time step forecast prediction depending on the indicator.

For example:

- `TODO` is defined every horu for the next 114 hours.
- `TODO` is defined every hour for the next 51 hours, and then every 3 hours.

Get the list of the available `forecast_horizons` using, once again, `get_coverage_description`.

```python
# retrieve the available times
coverage_axis['times']
```
