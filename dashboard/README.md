# AV Job Market Analysis Dashboard

## Overview

This Tableau dashboard provides an analysis of autonomous vehicle (AV) job postings, including monthly posting distribution, geographic distribution, and in-demand skills.

The dashboard is based on the published dataset snapshot dated **25 September 2026**.

## How to Open

1. Download `AV jobs market analysis_Final.twbx` from the `dashboard` directory.
2. Open the file using Tableau Desktop.
3. The workbook includes a packaged Hyper extract, so a live MySQL connection is not required to view the dashboard.

## Data Scope

- **Snapshot date:** 25 September 2026
- **Total AV-classified postings:** 2,902
- **Dashboard population:** 2,477 High-confidence AV-classified postings
- **Job status:** Both active and inactive postings are included.

The High-confidence filter was applied to reduce potential misclassification of non-AV roles. Confidence represents the certainty of the AV relevance classification, not the strength of AV relevance.

## Dashboard Visualisations

| Visualisation | Description |
|---|---|
| High Confidence AV Jobs | Number of High-confidence AV-classified postings |
| Total Companies | Number of companies represented in the filtered dataset |
| Monthly AV Job Postings | Distribution of postings by advertised posting month |
| Top 10 Hiring Countries | Countries with the highest numbers of postings |
| Top 10 In-Demand Skills | Most frequently mentioned skills in the filtered dataset |
| Skill Demand By Posting Month | Distribution of skill mentions by advertised posting month |

## Data Limitations

- **Single snapshot:** Monthly charts use advertised posting dates from the 25 September snapshot. They do not represent changes between weekly classified releases.
- **Date coverage:** Postings with missing dates or dates outside 2026 are excluded from monthly charts.
- **Unknown locations:** Country charts exclude 217 postings with unknown countries in the High-confidence subset.
- **Classification uncertainty:** High-confidence filtering reduces potential classification noise but does not guarantee that every included posting is directly AV-related.
- **Inactive postings:** Both active and inactive postings are included in the analysis.

## Data Refresh

The packaged workbook contains a Hyper extract from the 25 September 2026 release and can be opened without a live database connection.

Updating the MySQL database does **not automatically refresh** the packaged workbook.

To analyse a newer dataset, the Tableau data source must be refreshed or reconnected to the appropriate MySQL dashboard views. The updated workbook must then be validated, saved, and repackaged.

The current workbook represents a fixed snapshot, not live market data.




