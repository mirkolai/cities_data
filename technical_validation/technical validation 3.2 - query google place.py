import os
import json
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo


Your Google API KEY
API_KEY = "*********************************"

INPUT_DIR = "technical_validation_3_pairs"
OUTPUT_DIR = "technical_validation_3_google_results"

REFERENCE_YEAR = 2026
REFERENCE_MONTH = 6
REFERENCE_DAY = 15

os.makedirs(OUTPUT_DIR, exist_ok=True)

URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

HEADERS = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": API_KEY,
    "X-Goog-FieldMask": "routes.duration"
}


tf = TimezoneFinder()
timezone_cache = {}

def get_timezone(lat, lon):
    key = (round(float(lat), 4), round(float(lon), 4))

    if key not in timezone_cache:
        timezone_cache[key] = tf.timezone_at(lat=float(lat), lng=float(lon))

    return timezone_cache[key]


def get_local_noon(lat, lon):
    tz_name = get_timezone(lat, lon)

    if tz_name is None:
        raise ValueError(f"Timezone not found for lat={lat}, lon={lon}")

    local_dt = datetime(
        REFERENCE_YEAR,
        REFERENCE_MONTH,
        REFERENCE_DAY,
        12, 0, 0,
        tzinfo=ZoneInfo(tz_name)
    )

    return tz_name, local_dt.isoformat()


def get_transit_route(source_lat, source_lon, destination_lat, destination_lon):

    tz_name, departure_time = get_local_noon(source_lat, source_lon)

    body = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": float(source_lat),
                    "longitude": float(source_lon)
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": float(destination_lat),
                    "longitude": float(destination_lon)
                }
            }
        },
        "travelMode": "TRANSIT",
        "departureTime": departure_time
    }

    response = requests.post(URL, headers=HEADERS, json=body, timeout=60)
    print(response)
    response.raise_for_status()

    return {
        "timezone": tz_name,
        "departure_time": departure_time,
        "response": response.json()
    }


def save_checkpoint(df, output_file):
    tmp_file = output_file.with_suffix(".tmp.csv")
    df.to_csv(tmp_file, index=False)
    os.replace(tmp_file, output_file)


csv_files = sorted(Path(INPUT_DIR).glob("*.csv"))

print(f"Trovati {len(csv_files)} file")

for csv_file in csv_files:

    print(f"\n=== {csv_file.name} ===")

    df = pd.read_csv(csv_file)
    output_file = Path(OUTPUT_DIR) / csv_file.name

    total_rows = len(df)


    if output_file.exists():
        print(f"[RESUME] checkpoint found: {output_file}")

        df_old = pd.read_csv(output_file)

        if "google_json" not in df_old.columns:
            df_old["google_json"] = None
        if "departure_time" not in df_old.columns:
            df_old["departure_time"] = None
        if "timezone" not in df_old.columns:
            df_old["timezone"] = None

        google_jsons = df_old["google_json"].tolist()
        departure_times = df_old["departure_time"].tolist()
        timezones = df_old["timezone"].tolist()

    else:
        google_jsons = [None] * total_rows
        departure_times = [None] * total_rows
        timezones = [None] * total_rows


    for idx, row in df.iterrows():

        if (
            idx < len(google_jsons)
            and google_jsons[idx] is not None
            and str(google_jsons[idx]).strip() != ""
            and google_jsons[idx] != "nan"
        ):
            continue

        try:
            result = get_transit_route(
                source_lat=row["source_lat"],
                source_lon=row["source_lon"],
                destination_lat=row["destination_lat"],
                destination_lon=row["destination_lon"]
            )

            google_jsons[idx] = json.dumps(result["response"], ensure_ascii=False)
            departure_times[idx] = result["departure_time"]
            timezones[idx] = result["timezone"]

            print(f"[OK] {idx + 1}/{total_rows}")

        except Exception as e:

            google_jsons[idx] = json.dumps({"error": str(e)}, ensure_ascii=False)
            departure_times[idx] = None
            timezones[idx] = None

            print(f"[ERROR] {idx + 1}/{total_rows}: {e}")

        df["timezone"] = timezones
        df["departure_time"] = departure_times
        df["google_json"] = google_jsons

        save_checkpoint(df, output_file)

        time.sleep(5)

    print(f"SAVED: {output_file}")

print("\nCOMPLETED.")
