# Meteole

**Meteole** provides utilities to facilitate data retrieval from the Météo-France APIs using Python. It specifically supports the AROME and ARPEGE forecast models and vigilance bulletins.

## 🛠 Installation

```python
pip install meteole
```

## 🕐 Quickstart

### Obtain an API token or key

Create an account on [the Météo-France API portal](https://portail-api.meteofrance.fr/). Next, subscribe to the desired APIs (Arome, Arpege, etc.). Retrieve the API token (or key) by going to “Mes APIs” and then “Générer token”.

### 🌧️ AROME, ARPEGE

The flagship weather forecasting models of Météo-France are accessible via the Météo-France APIs.

| Characteristics  | AROME                | ARPEGE               |
|------------------|----------------------|----------------------|
| Resolution       | 1.3 km               | 10 km                |
| Update Frequency | Every 3 hours        | Every 6 hours        |
| Forecast Range   | Up to 51 hours       | Up to 114 hours      |

```python
from meteole import arome

arome_client = arome.AromeForecast(application_id=APPLICATION_ID)  # APPLICATION_ID found on portail.meteo-france.Fr

# let's look at the latest wind gusts
indicator = 'V_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND'

# or check any other indicator in the list
print(arome_client.indicators)

# get the latest MeteoFrance forecasts concerning this indicator
# all default parameters are printed to make sure you are in control
df_arome = arome_client.get_coverage(indicator)

# default height doesn't suit you? change it easily
df_arome = arome_client.get_coverage(indicator, height=10)
```

### ⚠️ VIGILANCE METEO FRANCE

Meteo France offers a vigilance bulletin that provides nationwide predictions of potential weather risks.

For data usage, access the predicted phenomena to trigger modeling based on the forecasts.

```python
from meteole import Vigilance

client = Vigilance(application_id=APPLICATION_ID)

df_phenomenon, df_timelaps = client.get_phenomenon() # pour accéder aux phénomènes prévus

textes_vigilance = client.get_textes_vigilance() # pour accéder aux bulletins de vigilance

client.get_vignette() # pour afficher les vignettes
```

<img src="assets/vignette_exemple.png" width="600" height="300" alt="vignette de vigilance">

To have more documentation from MeteoFrance in Vigilance Bulletin :
- [Meteo France Documentation](https://donneespubliques.meteofrance.fr/?fond=produit&id_produit=305&id_rubrique=50)
