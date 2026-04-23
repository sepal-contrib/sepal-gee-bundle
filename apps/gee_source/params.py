"""Static parameters for the GEE Source app."""

from pathlib import Path

# Root folder where every SEPAL module writes its results.
MODULE_RESULTS_DIR = Path.home() / "module_results"

# Per-app result directory — all extracted .js files land here.
RESULT_DIR = MODULE_RESULTS_DIR / "gee_source"

# Network timeout for HTTP calls against the Earth Engine Apps hosts, in seconds.
HTTP_TIMEOUT = 30

# User agent presented when scraping an Earth Engine App page.
USER_AGENT = "sepal-gee-bundle/gee_source (+https://github.com/sepal-contrib)"

# File extension used for the extracted source.
OUTPUT_EXTENSION = ".js"

# Prefix every Earth Engine App URL must start with.
EE_APP_URL_PREFIXES = ("https://",)
