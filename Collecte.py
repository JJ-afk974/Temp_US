import requests
import csv
from datetime import datetime
from zoneinfo import ZoneInfo


# ============================================================
# STATIONS
# ============================================================

stations = [
    (
        "New York",
        40.761,
        -73.864,
        "e1f10a1e78da46f5b10a1e78da96f525",
        "e",
        True,
    ),

    (
        "Miami",
        25.7954,
        -80.2901,
        "e1f10a1e78da46f5b10a1e78da96f525",
        "e",
        True,
    ),
]


# ============================================================
# MODELES OPEN-METEO
# ============================================================

MODELS = [
    ("ECMWF IFS", "ecmwf_ifs"),
    ("ECMWF AIFS", "ecmwf_aifs025_single"),
    ("GFS", "ncep_gfs_seamless"),
    ("HRRR", "ncep_hrrr_conus"),
    ("NBM", "ncep_nbm_conus"),
    ("NAM", "ncep_nam_conus"),
    ("ICON", "icon_global"),
    ("GEM", "cmc_gem_gdps"),
]


# ============================================================
# CONFIGURATION
# ============================================================

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
)

CSV_FILE = "temperatures_modeles.csv"

PARIS_TZ = ZoneInfo(
    "Europe/Paris"
)


# ============================================================
# NWS
# ============================================================

NWS_HEADERS = {
    "User-Agent": (
        "(temperatures-modeles-script, "
        "contact@example.com)"
    ),
    "Accept": "application/geo+json",
}


# ============================================================
# SESSION HTTP
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "temperatures-modeles-script/1.0"
    )
})


# ============================================================
# HEURE DE REQUETE
# ============================================================

def now_paris():
    return datetime.now(
        PARIS_TZ
    )


# ============================================================
# ARRONDI TEMPERATURE
# ============================================================

def round_temperature(value):

    if value is None:
        return None

    return int(
        round(float(value))
    )


# ============================================================
# OPEN-METEO
# ============================================================

def fetch_openmeteo(
    lat,
    lon,
    model_id
):

    params = {
        "latitude": lat,
        "longitude": lon,

        "hourly": "temperature_2m",

        "models": model_id,

        "forecast_days": 3,

        "timezone": "Europe/Paris",

        "temperature_unit": "fahrenheit",
    }

    response = session.get(
        OPEN_METEO_URL,
        params=params,
        timeout=30,
    )

    # --------------------------------------------------------
    # ERREUR
    # --------------------------------------------------------

    if response.status_code != 200:

        print()
        print(
            "ERREUR OPEN-METEO"
        )

        print(
            "HTTP :",
            response.status_code
        )

        print(
            "Model :",
            model_id
        )

        print(
            "URL :",
            response.url
        )

        try:

            print(
                "Réponse :",
                response.json()
            )

        except Exception:

            print(
                response.text
            )

        return None

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    try:

        return response.json()

    except Exception as e:

        print(
            "JSON invalide :",
            e
        )

        return None


# ============================================================
# EXTRACTION OPEN-METEO
# ============================================================

def get_openmeteo_daily(
    data,
    request_time
):

    if not data:
        return None

    hourly = data.get(
        "hourly"
    )

    if not hourly:

        print(
            "Pas de bloc hourly."
        )

        return None

    times = hourly.get(
        "time",
        []
    )

    temperatures = hourly.get(
        "temperature_2m",
        []
    )

    if not times:

        print(
            "Pas de timestamps."
        )

        return None

    if not temperatures:

        print(
            "Pas de températures."
        )

        return None

    # --------------------------------------------------------
    # Référence
    # --------------------------------------------------------

    reference = request_time.replace(
        minute=0,
        second=0,
        microsecond=0,
        tzinfo=None,
    )

    daily = {
        "J+0": [],
        "J+1": [],
        "J+2": [],
    }

    # --------------------------------------------------------
    # Données horaires
    # --------------------------------------------------------

    for time_str, temperature in zip(
        times,
        temperatures,
    ):

        try:

            forecast_time = (
                datetime.fromisoformat(
                    time_str
                )
            )

        except ValueError:

            continue

        # ----------------------------------------------------
        # H+X
        # ----------------------------------------------------

        delta_hours = (
            forecast_time - reference
        ).total_seconds() / 3600

        lead_hour = int(
            round(delta_hours)
        )

        # On ne prend que H+1 -> H+48
        if not (
            1 <= lead_hour <= 48
        ):

            continue

        # ----------------------------------------------------
        # J+X
        # ----------------------------------------------------

        day_offset = (
            forecast_time.date()
            - request_time.date()
        ).days

        if day_offset == 0:

            jour = "J+0"

        elif day_offset == 1:

            jour = "J+1"

        elif day_offset == 2:

            jour = "J+2"

        else:

            continue

        if temperature is not None:

            daily[jour].append(
                temperature
            )

    return daily


# ============================================================
# CREATION RESULTATS OPEN-METEO
# ============================================================

def process_openmeteo_model(
    station_name,
    lat,
    lon,
    model_name,
    model_id,
    request_time,
):

    print()
    print(
        f"--- Open-Meteo / {model_name} ---"
    )

    data = fetch_openmeteo(
        lat,
        lon,
        model_id,
    )

    if data is None:

        print(
            "Modèle ignoré."
        )

        return []

    daily = get_openmeteo_daily(
        data,
        request_time,
    )

    if daily is None:

        return []

    results = []

    request_time_str = (
        request_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    for jour in [
        "J+0",
        "J+1",
        "J+2",
    ]:

        values = daily[jour]

        if values:

            tmin = round_temperature(
                min(values)
            )

            tmax = round_temperature(
                max(values)
            )

        else:

            tmin = None
            tmax = None

        results.append({

            "Station": station_name,

            "Model": model_name,

            "RequestTime": (
                request_time_str
            ),

            "Jour": jour,

            "Tmin": tmin,

            "Tmax": tmax,
        })

        print(
            f"{jour} : "
            f"Tmin={tmin}°F | "
            f"Tmax={tmax}°F"
        )

    return results


# ============================================================
# WEATHER UNDERGROUND
# ============================================================

def fetch_wu(
    lat,
    lon,
    api_key,
    units,
    request_time,
):

    url = (
        "https://api.weather.com/v3/"
        "wx/forecast/hourly/15day"
    )

    params = {
        "apiKey": api_key,

        "geocode": (
            f"{lat},{lon}"
        ),

        "units": units,

        "language": "en-US",

        "format": "json",
    }

    response = session.get(
        url,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    times = data[
        "validTimeLocal"
    ]

    temperatures = data[
        "temperature"
    ]

    daily = {
        "J+0": [],
        "J+1": [],
        "J+2": [],
    }

    request_date = (
        request_time.date()
    )

    for time_str, temperature in zip(
        times,
        temperatures,
    ):

        try:

            dt = datetime.fromisoformat(
                time_str
            )

        except ValueError:

            continue

        offset = (
            dt.date()
            - request_date
        ).days

        if offset == 0:

            jour = "J+0"

        elif offset == 1:

            jour = "J+1"

        elif offset == 2:

            jour = "J+2"

        else:

            continue

        if temperature is not None:

            daily[jour].append(
                temperature
            )

    return daily


def process_wu(
    station_name,
    lat,
    lon,
    api_key,
    units,
    request_time,
):

    print()
    print(
        "--- Weather Underground ---"
    )

    results = []

    try:

        daily = fetch_wu(
            lat,
            lon,
            api_key,
            units,
            request_time,
        )

        request_time_str = (
            request_time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        for jour in [
            "J+0",
            "J+1",
            "J+2",
        ]:

            values = daily[jour]

            if values:

                tmin = round_temperature(
                    min(values)
                )

                tmax = round_temperature(
                    max(values)
                )

            else:

                tmin = None
                tmax = None

            results.append({

                "Station": station_name,

                "Model": "WU",

                "RequestTime": (
                    request_time_str
                ),

                "Jour": jour,

                "Tmin": tmin,

                "Tmax": tmax,
            })

            print(
                f"{jour} : "
                f"Tmin={tmin}°F | "
                f"Tmax={tmax}°F"
            )

    except Exception as e:

        print(
            "ERREUR WU :",
            e
        )

    return results


# ============================================================
# NWS
# ============================================================

def fetch_nws(
    lat,
    lon,
    request_time,
):

    points_url = (
        f"https://api.weather.gov/"
        f"points/{lat},{lon}"
    )

    response = requests.get(
        points_url,
        headers=NWS_HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    forecast_url = (
        response.json()
        ["properties"]
        ["forecastHourly"]
    )

    response = requests.get(
        forecast_url,
        headers=NWS_HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    periods = (
        response.json()
        ["properties"]
        ["periods"]
    )

    daily = {
        "J+0": [],
        "J+1": [],
        "J+2": [],
    }

    request_date = (
        request_time.date()
    )

    for period in periods:

        try:

            dt = datetime.fromisoformat(
                period["startTime"]
            )

        except ValueError:

            continue

        offset = (
            dt.date()
            - request_date
        ).days

        if offset == 0:

            jour = "J+0"

        elif offset == 1:

            jour = "J+1"

        elif offset == 2:

            jour = "J+2"

        else:

            continue

        temperature = period.get(
            "temperature"
        )

        if temperature is not None:

            daily[jour].append(
                temperature
            )

    return daily


def process_nws(
    station_name,
    lat,
    lon,
    request_time,
):

    print()
    print(
        "--- NWS ---"
    )

    results = []

    try:

        daily = fetch_nws(
            lat,
            lon,
            request_time,
        )

        request_time_str = (
            request_time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        for jour in [
            "J+0",
            "J+1",
            "J+2",
        ]:

            values = daily[jour]

            if values:

                tmin = round_temperature(
                    min(values)
                )

                tmax = round_temperature(
                    max(values)
                )

            else:

                tmin = None
                tmax = None

            results.append({

                "Station": station_name,

                "Model": "NWS",

                "RequestTime": (
                    request_time_str
                ),

                "Jour": jour,

                "Tmin": tmin,

                "Tmax": tmax,
            })

            print(
                f"{jour} : "
                f"Tmin={tmin}°F | "
                f"Tmax={tmax}°F"
            )

    except Exception as e:

        print(
            "ERREUR NWS :",
            e
        )

    return results


# ============================================================
# EXECUTION
# ============================================================

all_results = []


for (
    station_name,
    lat,
    lon,
    api_key,
    units,
    source_nws,
) in stations:

    print()
    print()
    print("#" * 70)

    print(
        f"STATION : {station_name}"
    )

    print("#" * 70)

    # Une seule RequestTime pour toutes
    # les sources de cette station.

    request_time = now_paris()

    print(
        "RequestTime :",
        request_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    # --------------------------------------------------------
    # OPEN-METEO
    # --------------------------------------------------------

    for model_name, model_id in MODELS:

        results = process_openmeteo_model(
            station_name,
            lat,
            lon,
            model_name,
            model_id,
            request_time,
        )

        all_results.extend(
            results
        )

    # --------------------------------------------------------
    # WU
    # --------------------------------------------------------

    results = process_wu(
        station_name,
        lat,
        lon,
        api_key,
        units,
        request_time,
    )

    all_results.extend(
        results
    )

    # --------------------------------------------------------
    # NWS
    # --------------------------------------------------------

    if source_nws:

        results = process_nws(
            station_name,
            lat,
            lon,
            request_time,
        )

        all_results.extend(
            results
        )


# ============================================================
# EXPORT
# ============================================================

FIELDNAMES = [
    "Station",
    "Model",
    "RequestTime",
    "Jour",
    "Tmin",
    "Tmax",
]


with open(
    CSV_FILE,
    "w",
    newline="",
    encoding="utf-8",
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=FIELDNAMES,
    )

    writer.writeheader()

    writer.writerows(
        all_results
    )
