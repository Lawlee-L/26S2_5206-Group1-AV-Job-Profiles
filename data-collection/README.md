# Data Collection

## AV Company List

The AV company list is maintained collaboratively in Excel Online and is the current source of truth for the team.

[Open the AV Company List in Excel Online](https://uniwa-my.sharepoint.com/:x:/r/personal/24732339_student_uwa_edu_au/Documents/CITS5206%20Capstone/AV%20company%20list.xlsx?d=wbb74df523aa941dbb3712e1b43257003&csf=1&web=1&e=p6ZwOm)

Access is managed through UWA SharePoint. If the workbook does not open, request access from the document owner.

## Charts

Generated charts are stored in [`charts/`](./charts/).

## Data Acquisition MVP

The implementation of the Scrapy-to-Parquet/DuckDB collection workflow is in
[`mvp-data-acquisition/`](./mvp-data-acquisition/). It contains one spider per
implemented company, shared ATS adapters, offline tests, and its own operating
and development documentation.
