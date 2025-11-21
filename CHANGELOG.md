# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.3] - November, 2025

### Bugs

* INDICATORS and INSTANT_INDICATORS attributes of WeatherForecast object where not always in sync with
  the actual capabilities. Changed these attributes to properties that compute these lists dynamically
  from the capabilities attribute. Changed their name to lowercase, since they are not constants anymore.
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
