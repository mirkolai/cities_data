import os
import json
import pandas as pd
import numpy as np
from glob import glob
from scipy.stats import spearmanr, pearsonr

INPUT_DIR = "technical_validation_3_google_results"
OUTPUT_FILE = ("technical validation - summary.csv")


def extract_duration(json_str):
    try:
        data = json.loads(json_str)
        return float(data["routes"][0]["duration"].replace("s", ""))
    except Exception:
        return np.nan


def compute_metrics(df):
    df = df.dropna(subset=["time", "duration"])

    if len(df) < 2:
        return None

    time = df["time"].astype(float)
    duration = df["duration"].astype(float)

    mae = np.mean(np.abs(time - duration))
    rmse = np.sqrt(np.mean((time - duration) ** 2))
    bias = np.mean(time - duration)

    pearson = pearsonr(time, duration)[0] if len(df) > 1 else np.nan
    spearman = spearmanr(time, duration)[0] if len(df) > 1 else np.nan

    return {
        "n_edges": len(df),
        "mae": mae,
        "rmse": rmse,
        "bias": bias,
        "pearson": pearson,
        "spearman": spearman,
    }


def process_file(filepath):
    df = pd.read_csv(filepath)

    df["duration"] = df["google_json"].apply(extract_duration)

    metrics = compute_metrics(df)

    if metrics is None:
        return None

    city_name = os.path.basename(filepath).replace(".csv", "")

    metrics["city"] = city_name

    return metrics


def main():
    files = glob(os.path.join(INPUT_DIR, "*.csv"))

    results = []

    for f in files:
        res = process_file(f)
        if res:
            results.append(res)

    out_df = pd.DataFrame(results)

    cols = ["city", "n_edges", "mae", "rmse", "bias", "pearson", "spearman"]
    out_df = out_df[cols]

    out_df.to_csv(OUTPUT_FILE, index=False)

    print(f"Saved metrics for {len(out_df)} cities -> {OUTPUT_FILE}")

    print(f"Saved metrics for {len(out_df)} cities -> {OUTPUT_FILE}")


    metrics_cols = ["mae", "rmse", "bias", "pearson", "spearman"]

    summary = pd.DataFrame({
        "min": out_df[metrics_cols].min(),
        "max": out_df[metrics_cols].max(),
        "mean": out_df[metrics_cols].mean(),
        "median": out_df[metrics_cols].median(),
        "std": out_df[metrics_cols].std()
    })

    print("\n=== SUMMARY STATISTICS ===")
    print(summary.round(4))


    q1 = out_df["spearman"].quantile(0.25)
    q3 = out_df["spearman"].quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr

    outliers = out_df[out_df["spearman"] < lower_bound] \
        .sort_values("spearman")

    print("\n=== SPEARMAN OUTLIERS (IQR METHOD) ===")
    print(f"Threshold: {lower_bound:.3f}")

    if len(outliers):
        print(
            outliers[
                ["city", "spearman", "pearson", "mae", "rmse", "bias"]
            ].to_string(index=False)
        )
    else:
        print("No outliers detected.")

    positive_bias = out_df[out_df["bias"] > 0] \
        .sort_values("bias", ascending=False)

    print("\n=== HIGHEST POSITIVE BIAS CITIES ===")

    if len(positive_bias):
        print(
            positive_bias[
                ["city", "bias", "mae", "rmse", "pearson", "spearman"]
            ]
            .head(10)
            .to_string(index=False)
        )
    else:
        print("No positive bias cities found.")

if __name__ == "__main__":
    main()