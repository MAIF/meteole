<p align="center">
  <a href="https://maif.github.io/meteole"><img src="docs/pages/assets/img/svg/meteole-fond-clair.svg" alt="meteole" width="50%"></a>
</p>
<p align="center">
    <em>Easy access to Météo-France weather models and data</em>
</p>
<p align="center">
  <img src="https://github.com/MAIF/meteole/actions/workflows/ci-cd.yml/badge.svg?branch=main" alt="CI">
  <img src="https://img.shields.io/badge/coverage-89%25-dark_green" alt="Coverage">
  <img src="https://img.shields.io/pypi/v/meteole" alt="Versions">
  <img src="https://img.shields.io/pypi/pyversions/meteole" alt="Python">
  <img src="https://img.shields.io/pypi/dm/meteole" alt="Downloads">
</p>

---

**Documentation:** [https://pages.github.com/MAIF/meteole/home](https://pages.github.com/MAIF/meteole/home)

**Repository:** [https://github.com/MAIF/meteole](https://github.com/MAIF/meteole)

---

## Overview

**Meteole** is a Python library designed to simplify accessing weather data from the Météo-France APIs. It provides:

- **Automated token management**: Simplify authentication with a single `application_id`.
- **Unified model usage**: AROME and ARPEGE forecasts with a consistent interface.
- **User-friendly parameter handling**: Intuitive management of key weather forecasting parameters.
- **Seamless data integration**: Directly export forecasts as Pandas DataFrames
- **Vigilance bulletins**: Retrieve real-time weather warnings across France.

Perfect for data scientists, meteorologists, and developers, Meteole helps integrate weather forecasts into projects effortlessly.

### Installation

```python
pip install meteole
```

## 🕐 Quickstart

### Step 1: Obtain an API token or key

Create an account on [the Météo-France API portal](https://portail-api.meteofrance.fr/). Next, subscribe to the desired APIs (Arome, Arpege, etc.). Retrieve the API token (or key) by going to “Mes APIs” and then “Générer token”.

### Step 2: Fetch Forecasts from AROME and ARPEGE

Meteole allows you to retrieve forecasts for a wide range of weather indicators. Here's how to get started with AROME and ARPEGE:

| Characteristics  | AROME                | ARPEGE               |
|------------------|----------------------|----------------------|
| Resolution       | 1.3 km               | 10 km                |
| Update Frequency | Every 3 hours        | Every 6 hours        |
| Forecast Range   | Up to 51 hours       | Up to 114 hours      |

```python
from meteole import AromeForecast

# Initialize the AROME forecast client
arome_client = AromeForecast(application_id=APPLICATION_ID)  # APPLICATION_ID found on portail.meteo-france.Fr

# Check indicators available
print(arome_client.indicators)

# Fetch weather data
df_arome = arome_client.get_coverage(
    indicator="V_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",  # Optional: if not, you have to fill coverage_id
    run="2025-01-10T00:00:00Z",                                                # Optional: forecast start time
    interval=None,                                                             # Optional: time range for predictions
    forecast_horizons=[0, 1, 2],                                               # Optional: prediction times (in hours)
    heights=[10],                                                              # Optional: height above ground level  
    pressures=None,                                                            # Optional: pressure level
    coverage_id=None                                                           # Optional: an alternative to indicator/run/interval
)
```
Note: The coverage_id can be used instead of indicator, run, and interval.

The usage of ARPEGE is identical to AROME, except that you initialize the `ArpegeForecast` class

### Step 3: Explore Parameters and Indicators
#### Discover Available Indicators
Use the `get_capabilities()` method to list all available indicators, run times, and intervals:

```
indicators = arome_client.get_capabilities()
print(indicators)
```

#### Fetch Description for a Specific Indicator
Understand the required parameters (`forecast_horizons`, `heights`, `pressures`)  for any indicator using `get_description()`:

```
description = arome_client.get_description(coverage_id)
print(description)
```

#### Geographical Coverage
The geographical coverage of forecasts can be customized using the lat and long parameters in the get_coverage method. By default, Meteole retrieves data for the entire metropolitan France.

#### Fetch Forecasts for Multiple Indicators
The `get_combined_coverage` method allows you to retrieve weather data for multiple indicators at the same time, streamlining the process of gathering forecasts for different parameters (e.g., temperature, wind speed, etc.). For detailed guidance on using this feature, refer to this [tutorial](./tutorial/Fetch_forecast_for_multiple_indicators.ipynb).

Explore detailed examples in the [tutorials folder](./tutorial) to quickly get started with Meteole.

### ⚠️ VIGILANCE METEO FRANCE
Meteo France provides nationwide vigilance bulletins, highlighting potential weather risks. These tools allow you to integrate weather warnings into your workflows, helping trigger targeted actions or models.

```python
from meteole import Vigilance

vigi = Vigilance(application_id=APPLICATION_ID)

df_phenomenon, df_timelaps = vigi.get_phenomenon()

bulletin = vigi.get_bulletin()

vigi.get_vignette()
```

<img src="docs/pages/assets/img/png/vignette_exemple.png" width="600" height="300" alt="vignette de vigilance">

To have more documentation from Meteo-France in Vigilance Bulletin :
- [Meteo France Documentation](https://donneespubliques.meteofrance.fr/?fond=produit&id_produit=305&id_rubrique=50)

## Contributing

Contributions are *very* welcome!

If you see an issue that you'd like to see fixed, the best way to make it happen is to help out by submitting a pull request implementing it.

Refer to the [CONTRIBUTING.md](./CONTRIBUTING.md) file for more details about the workflow,
and general hints on how to prepare your pull request. You can also ask for clarifications or guidance in GitHub issues directly.

## License

This project is Open Source and available under the Apache 2 License.

## 🤝 Contributors
The development of Meteole was inspired by the excellent work in the [meteofranceapi](https://github.com/antoinetavant/meteofranceapi) repository by Antoine Tavant.
