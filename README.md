# Job Market Analysis

Analysis of Australian ICT job vacancies against IT graduate supply, writer jobs, and US software developer jobs.

## Files

- `main.py` uses pandas to clean source data into a useful csv
- `master_data.csv` is the output of `main.py` and is the input for analysis
- `report.pbix` is the Power BI dashboard
- `report.pdf` is a PDF export

## Method

Raw values are not compared in the analysis due to the measured variables being affected by many factors which could skew conclusions. That's why values were calculated with respect to a base year at 100%.

## Data Sources

- Jobs and Skills Australia: Internet Vacancy Index
- Department of Education: Higher Education Statistics, Section 14
- FRED: Indeed Job Postings Index (IHLIDXUSTPSOFTDEVE)

## Run

```sh
pip install pandas openpyxl
python main.py
```

The `master_data.csv` file can be used for analysis.