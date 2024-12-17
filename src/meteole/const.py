API_BASE_URL = "https://public-api.meteofrance.fr/public/"

EXPIRED_TOKEN_CODE = 401
SUCCESS_CODES = [200, 202, 201]
PARAMETER_ERROR_CODE = 400
INVALID_TOKEN_CODE = 401
FORBIDDEN_CODE = 403
THROTTLED_CODE = 429
INTERNAL_ERROR_CODE = 500
UNUVAILABLE_CODE = 503
BACKEND_ERROR_CODE = 504
MISSING_DATA_CODE = 404
SPECIFIC_ERROR = 502

PRECISION_FLOAT_TO_STR = {0.25: "025", 0.1: "01", 0.05: "005", 0.01: "001", 0.025: "0025"}

FRANCE_METRO_LONGITUDES = (-5.1413, 9.5602)
FRANCE_METRO_LATITUDES = (41.33356, 51.0889)

dict_phenomenon_id = {
    "1": "wind",
    "2": "rain",
    "3": "storm",
    "4": "flood",
    "5": "snow_ice",
    "6": "heat_wave",
    "7": "extreme_cold",
    "8": "avalanches",
    "9": "waves_submergence",
}
