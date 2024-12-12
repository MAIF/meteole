There is one reason for using **Meteole**:

> Easy access Météo-France forecast and vigilance data

## Before Meteole :cloud_with_rain:

Accessing weather data from Météo-France via Python can be a bit cumbersome and time-consuming. 

It involves:

* diving into Météo-France documentation
* handling expiring tokens
* managing XML responses
* explore specificities for every indicator
* parse responses to get a clean dataframe

## After Meteole :sunny:

**Meteole** allows to quickly fetch tidy pandas dataframes full of weather-rich data:

* By handling the API boilerplate;
* By providing simple and well-documented function;
* By using heuristics when necessary parameters are not provided ;
