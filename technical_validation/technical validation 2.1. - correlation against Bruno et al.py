import pandas as pd
import csv
from scipy.stats import pearsonr

citta_minuti = {}
with open('technical validation 1. proximity bruno et al.txt', 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter='\t')
    for row in reader:
        if len(row) != 2:
            continue
        città, tempo = row
        città = place_name = città.strip('"')

        minuti, secondi = map(int, tempo.strip().split(':'))
        citta_minuti[città] = minuti if secondi == 0 else minuti + 1

citta_proximity_media = {}
citta_proximity = {}


for place_name in citta_minuti.keys():
    try:
        df = pd.read_json(f'../processed_data/{place_name}.json.gz', compression='gzip')


    except FileNotFoundError:
        print(f"Missing input files for {place_name}, skipping.")
        continue

    df = df.rename(columns={'diversity': 'entropy'})

    def avg_proximity_disaggregated(x):

        return sum([x for x in x.values()] + [61] * (7 - (len(list(x.keys()))))) / len(x)


    df['avg_proximity'] = df['proximity_disaggregated'].apply(avg_proximity_disaggregated)

    df_filtered = df[df['avg_proximity'] <= 60]
    if len(df_filtered) > 0:
        mean_proximity_city = df_filtered['avg_proximity'].mean()
        citta_proximity_media[place_name] = mean_proximity_city
    else:
        citta_proximity_media[place_name] = None

    citta_proximity[place_name]=df['proximity'].mean()

common_cities = set(citta_minuti.keys()) & set(citta_proximity.keys())
minutes_list = [citta_minuti[c] for c in common_cities]
proximity_list = [citta_proximity[c] for c in common_cities]

minutes_list_filtered = []
proximity_list_filtered = []
for m, p in zip(minutes_list, proximity_list):
    if p is not None:
        minutes_list_filtered.append(m)
        proximity_list_filtered.append(p)
correlation, p_value = pearsonr(minutes_list_filtered, proximity_list_filtered)

print("Correlation between CSV minutes and the city's average proximity:", correlation)
print("p-value:", p_value)

common_cities = set(citta_minuti.keys()) & set(citta_proximity_media.keys())
minutes_list = [citta_minuti[c] for c in common_cities]
proximity_list = [citta_proximity_media[c] for c in common_cities]


minutes_list_filtered = []
proximity_list_filtered = []
for m, p in zip(minutes_list, proximity_list):
    if p is not None:
        minutes_list_filtered.append(m)
        proximity_list_filtered.append(p)
correlation, p_value = pearsonr(minutes_list_filtered, proximity_list_filtered)

print("Correlation between CSV minutes and the city's mean avg_proximity:", correlation)
print("p-value:", p_value)


import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr

cities = (
    set(citta_minuti.keys())
    & set(citta_proximity.keys())
    & set(citta_proximity_media.keys())
)

city_names = []
minutes = []
proximity = []
avg_proximity = []

for city in cities:
    p = citta_proximity[city]
    ap = citta_proximity_media[city]

    if p is not None and ap is not None:
        city_names.append(city)
        minutes.append(citta_minuti[city])
        proximity.append(p)
        avg_proximity.append(ap)

r_prox, p_prox = pearsonr(minutes, proximity)
r_avg, p_avg = pearsonr(minutes, avg_proximity)

sns.set_style("whitegrid")

fig, axes = plt.subplots(1, 2, figsize=(12, 5))


sns.regplot(
    x=minutes,
    y=proximity,
    ax=axes[0],
    scatter_kws={"alpha": 0.7, "s": 50},
    line_kws={"color": "red"}
)

axes[0].set_xlabel("Bruno et al. (2024) (minutes)")
axes[0].set_ylabel("Mean proximity  (minutes)")
axes[0].set_title(
    f"Mean proximity vs Bruno et al.\nr = {r_prox:.2f}, p = {p_prox:.3g}"
)

coef = np.polyfit(minutes, proximity, 1)
pred = np.polyval(coef, minutes)
residuals = np.abs(np.array(proximity) - pred)

outlier_idx = np.argsort(residuals)[-5:]

for i in outlier_idx:
    axes[0].annotate(
        city_names[i].split(",")[0].split("(")[0].replace(" Metropolitana", "").replace("Región Metropolitana de ", "").replace(
                " Kommune", "").replace("Greater ", "").replace("City of ", "").replace("Municipality of ", "").strip(),
        (minutes[i], proximity[i]),
        fontsize=8,
        xytext=(5, 5),
        textcoords="offset points"
    )


sns.regplot(
    x=minutes,
    y=avg_proximity,
    ax=axes[1],
    scatter_kws={"alpha": 0.7, "s": 50},
    line_kws={"color": "red"}
)

axes[1].set_xlabel("Bruno et al. (2024) (minutes)")
axes[1].set_ylabel("Mean avg proximity (minutes)")
axes[1].set_title(
    f"Mean avg proximity vs Bruno et al.\nr = {r_avg:.2f}, p = {p_avg:.3g}"
)

coef = np.polyfit(minutes, avg_proximity, 1)
pred = np.polyval(coef, minutes)
residuals = np.abs(np.array(avg_proximity) - pred)

outlier_idx = np.argsort(residuals)[-5:]

for i in outlier_idx:
    axes[1].annotate(
        city_names[i].split(",")[0].split("(")[0].replace(" Metropolitana", "").replace("Región Metropolitana de ", "").replace(
                " Kommune", "").replace("Greater ", "").replace("City of ", "").replace("Municipality of ", "").strip(),
        (minutes[i], avg_proximity[i]),
        fontsize=8,
        xytext=(5, 5),
        textcoords="offset points"
    )

plt.tight_layout()
plt.savefig(
    "technical_validation_1.png",
    dpi=300,
    bbox_inches="tight"
)
plt.show()
