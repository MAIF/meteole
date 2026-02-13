# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.6] - February, 2026
### Features
* Added the ability to retrieve observations from a single station at a time.
* Updated tests and documentation to reflect these additions
See #21

## [0.2.5] - January, 2026
### Bugs
Depending on the indicators, the geographic boundary envelope of the indicators may have a height component or other components.
The current code does not take this into account.
See PR #62

## [0.2.4] - December, 2025
### Features
* Added a way to call the get_coverage method of WeatherForecast with floats for lat, long (instead of tuples only)
  to get forecast at a specific location (nearest grid point).
* Added a check on the lat, long parameters of get_coverage so that the closest gridpoint is used
* Added min and max available coordinates to get_coverage_description output
* Updated tests and documentation to reflect these changes

## [0.2.3] - November, 2025

### Bugs

* `INDICATORS` and `INSTANT_INDICATORS` attributes of WeatherForecast object where not always in sync with
  the actual capabilities. Changed these attributes to properties that compute these lists dynamically
  from the `capabilities` attribute. Changed their name to lowercase (`indicators`, `instant_indicators`), since they are not constants anymore.
  (`DeprecationWarning` about use of `INDICATORS` and `INSTANT_INDICATORS`)
  See issue #54.

## [0.2.2] - November, 2025

### Features

* Support for Météo-France ensemble model `PE-ARPEGE` and `PE-AROME` (#38)

## [0.2.1] - August, 2025

### Features

* Support for Python3.12 and Python 3.13

## [0.2.0] - January, 2025

### Features

* Support for Météo-France models `AROME PI` and `PIAF` (#27)
* Add an optional temporary directory: `temp_dir` (#28)
