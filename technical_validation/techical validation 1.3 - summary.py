import pandas as pd


df = pd.read_csv("technical validation 1 - summary.csv")


summary = (
    df.groupby("category")
      .agg(
          n_cities=("city", "count"),
          n_significant=("pvalue", lambda x: (x < 0.05).sum())
      )
)

summary["pct_significant"] = (
    100 * summary["n_significant"] / summary["n_cities"]
)

summary = summary.sort_values("pct_significant", ascending=False)

print(summary)
