Ensure that you have correctly installed **Meteole** before, check the [Installation](installation.md) page :wrench:

## Get a token, an API key or an application ID

1. Create an account on [the Météo-France API portal](https://portail-api.meteofrance.fr/).
2. Subscribe to the desired services (Arome, Arpege, etc.).
3. Retrieve the API token (or key) by going to "Mes APIs" and then "Générer token".

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

Meteole allows you to retrieve forecasts for a wide range of weather indicators. Here's how to get started with AROME and ARPEGE:

| Characteristics  | AROME                | ARPEGE               |
|------------------|----------------------|----------------------|
| Resolution       | 1.3 km               | 10 km                |
| Update Frequency | Every 3 hours        | Every 6 hours        |
| Forecast Range   | Up to 51 hours       | Up to 114 hours      |

```python
from meteole import AromeForecast

# Configure the logger to provide information on data recovery: recovery status, default settings, etc.
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meteole")

# Initialize the AROME forecast client
arome_client = AromeForecast(application_id=APPLICATION_ID)  # APPLICATION_ID found on portail.meteo-france.Fr

# Check indicators available
print(arome_client.INDICATORS)

# Fetch weather data
df_arome = arome_client.get_coverage(
    indicator="V_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",  # Optional: if not, you have to fill coverage_id
    run="2025-01-10T00.00.00Z",                                                # Optional: forecast start time
    interval=None,                                                             # Optional: time range for predictions
    forecast_horizons=[
        dt.timedelta(0),
        dt.timedelta(1),
        dt.timedelta(2),
    ],                                               # Optional: prediction times (in hours)
    heights=[10],                                                              # Optional: height above ground level
    pressures=None,                                                            # Optional: pressure level
    long = (-5.1413, 9.5602),                                                  # Optional: longitude
    lat = (41.33356, 51.0889),                                                 # Optional: latitude
    coverage_id=None                                                           # Optional: an alternative to indicator/run/interval
)
```

The `get_combined_coverage` method allows you to retrieve weather data for multiple indicators at the same time, streamlining the process of gathering forecasts for different parameters (e.g., temperature, wind speed, etc.). For detailed guidance on using this feature, refer to this [tutorial](https://github.com/MAIF/meteole/tree/docs/update_readme/tutorial/tutorial/Fetch_forecast_for_multiple_indicators.ipynb).