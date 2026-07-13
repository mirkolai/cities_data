# Cleaned Urban Accessibility Dataset

This repository contains the cleaned and curated datasets used in the study:

> **Understanding the interplay between urban segregation and accessibility to services with network analysis**
> **Mirko Lai, Anna Sapienza, Salvatore Vilella, Massimo Canonico, Federica Cena, Giancarlo Ruffo**
> *PLOS ONE*, Published: April 1, 2026
> https://doi.org/10.1371/journal.pone.0342156

Following the publication of the paper, we decided to make the processed datasets openly available to the scientific community to facilitate reproducibility, comparative analyses, and future research on urban accessibility, transport networks, and socio-spatial inequalities.

---

# About the study

The paper investigates the relationship between accessibility to urban services and transport connectivity through the lens of the **15-minute city** paradigm.

Using a network-based analytical framework, cities are modeled as complex spatial networks where accessibility is measured from the distribution of Points of Interest (PoIs), while transport connectivity is quantified using network centrality measures. The study explores whether highly localized accessibility models may unintentionally reinforce spatial segregation.

The analysis shows that neighborhoods with better access to services generally also benefit from better transport connectivity. However, this relationship is not socially uniform. In several cities, lower-income neighborhoods tend to experience both lower accessibility and weaker connectivity, while some higher-income neighborhoods exhibit similar patterns, suggesting possible forms of voluntary isolation. These findings highlight that improving proximity to services alone is not sufficient to guarantee equitable urban development.

---

# About this repository

The original datasets produced during the study have been cleaned, standardized, and organized to facilitate their reuse.

The repository is intended to provide researchers with ready-to-use data, avoiding the need to repeat the complete data acquisition and processing pipeline before performing analyses.

These datasets can support research in several areas, including:

* urban accessibility;
* transport network analysis;
* spatial inequality;
* urban morphology;
* comparative studies across cities;
* accessibility-based urban planning;
* mobility simulation;
* network science;
* agent-based modeling;
* socio-economic analyses when integrated with external demographic datasets.

The cleaned datasets can also serve as benchmarks for developing and validating new indicators of accessibility and transport connectivity.

---

# Technical validation

Before publication, all released datasets underwent a technical validation process to ensure consistency, completeness, and reproducibility.

The repository also includes the processed outputs used during the validation stage.

---

# Data provenance

All original data were collected exclusively from publicly available sources, including:

* OpenStreetMap (road networks and Points of Interest)
* WorldPop (population estimates)
* Transitland (GTFS public transport feeds)
* Italian Ministry of Economy and Finance (average income data for Italian cities)


The technical validation additionally employed the following independent data sources:

* Overture Maps, to assess the completeness and spatial distribution of the Points of Interest (PoIs) extracted from OpenStreetMap.
* Google Places API, to validate the consistency of the estimated public transport travel times.

---

# Raw data and reproducibility

This repository contains **only the cleaned and processed datasets**.

Researchers interested in reproducing the complete data generation pipeline or generating datasets for additional cities should use the companion repository:

https://github.com/mirkolai/cities

That repository contains:

* the complete source code used in the paper;
* scripts for downloading the original datasets from public providers;
* preprocessing pipelines;
* construction of road and public transport networks;
* computation of accessibility metrics;
* clustering of urban areas;
* computation of transport connectivity (closeness centrality);
* scripts used to reproduce all figures and analyses presented in the publication.

By executing the provided workflow, users can reproduce the datasets from scratch or extend the analysis to cities not included in the original study.

---

# License

The datasets in this repository are released under the **MIT License** unless otherwise specified.

Please remember that the original data providers (OpenStreetMap, WorldPop, Transitland, and other external sources) are distributed under their own respective licenses, which remain applicable to the original data.

