import datetime
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

IVI_PATH = "data/ivi_march_2026.xlsx"
GRAD_PATH = "data/2024_Section14_Award_Course_Completions.xlsx"
FRED_SOFT = "data/IHLIDXUSTPSOFTDEVE.csv"

AU_BASE_YEAR = 2015  # au series indexed here
US_BASE_YEAR = 2020  # fred data starts feb 2020, earliest full year is 2020

OUTPUT = "master_data.csv"


def index_to(series: pd.Series, base_year: int) -> pd.Series:
    base = series.loc[base_year]
    if base == 0 or pd.isna(base):
        raise ValueError(f"base year {base_year} is zero or missing")
    return (series / base * 100).round(2)


log.info("loading IVI")
ivi = pd.read_excel(IVI_PATH, sheet_name="Australia", header=0)
ivi = ivi[ivi["state"] == "AUST"].copy()
ivi["ANZSCO_CODE"] = pd.to_numeric(ivi["ANZSCO_CODE"], errors="coerce")
date_cols = [c for c in ivi.columns if isinstance(c, datetime.datetime)]


def ivi_series(codes: list[int], label: str) -> pd.Series:
    rows = ivi[ivi["ANZSCO_CODE"].isin(codes)][date_cols].sum()
    long = rows.reset_index()
    long.columns = ["date", "vacancies"]
    long["year"] = pd.to_datetime(long["date"]).dt.year
    annual = long.groupby("year")["vacancies"].sum() / 12
    log.info("%s: %d years", label, len(annual))
    return annual


au_ict = ivi_series([2612, 2613, 2621], "au_ict")
au_authors = ivi_series([2122], "au_authors_editors")
au_journo = ivi_series([2124], "au_journalists")
au_writers = ivi_series([2122, 2124], "au_writers_combined")

log.info("loading graduation data")
grad = pd.read_excel(GRAD_PATH, sheet_name="14.3", header=2)
grad_it = grad[grad["Broad Field of Education"] == "Information Technology"].copy()
year_cols = [c for c in grad_it.columns if isinstance(c, int)]


def clean(v):
    return 0 if v == "< 5" else pd.to_numeric(v, errors="coerce")


for col in year_cols:
    grad_it[col] = grad_it[col].apply(clean)


def grad_row(citizenship: str) -> pd.Series:
    row = grad_it[grad_it["Citizenship"] == citizenship]
    if row.empty:
        raise ValueError(f"citizenship row '{citizenship}' not found")
    s = row[year_cols].iloc[0].astype(int)
    s.index = s.index.astype(int)  # ensure int year index
    return s


domestic_grads = grad_row("Domestic Students")
total_grads = grad_row("All Students")


def load_fred(path: str, label: str) -> pd.Series:
    log.info("loading FRED: %s", label)
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        log.warning("FRED file not found: %s so column will be null", path)
        return pd.Series(dtype=float)
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")  # '.' = missing in FRED
    df = df.dropna(subset=["value"])
    df["year"] = df["date"].dt.year
    annual = df.groupby("year")["value"].mean()  # mean of daily readings = annual avg
    log.info(
        "%s: %d years (%d to %d)",
        label,
        len(annual),
        annual.index.min(),
        annual.index.max(),
    )
    return annual


us_software = load_fred(FRED_SOFT, "us_software_dev")

years = list(range(2015, 2026))
df = pd.DataFrame({"year": years}).set_index("year")

# raw au vacancy values (avg monthly, for reference)
df["au_ict_raw"] = au_ict.reindex(years)
df["au_writers_raw"] = au_writers.reindex(years)
df["au_authors_raw"] = au_authors.reindex(years)
df["au_journo_raw"] = au_journo.reindex(years)

# au graduation headcounts
df["domestic_it_grads"] = domestic_grads.reindex(years)
df["total_it_grads"] = total_grads.reindex(years)

# au indices (2015 = 100)
df["au_ict_index"] = index_to(au_ict.reindex(years).dropna(), AU_BASE_YEAR).reindex(
    years
)
df["au_writers_index"] = index_to(
    au_writers.reindex(years).dropna(), AU_BASE_YEAR
).reindex(years)
df["au_authors_index"] = index_to(
    au_authors.reindex(years).dropna(), AU_BASE_YEAR
).reindex(years)
df["au_journo_index"] = index_to(
    au_journo.reindex(years).dropna(), AU_BASE_YEAR
).reindex(years)
df["au_grad_index"] = index_to(
    domestic_grads.reindex(years).dropna(), AU_BASE_YEAR
).reindex(years)

# 2020 us comparison
df["au_ict_index_2020"] = index_to(au_ict.reindex(years).dropna(), 2020).reindex(years)

# us indices (2020 = 100) null for 2015-2019, data starts feb 2020
if not us_software.empty:
    df["us_software_index"] = index_to(
        us_software.reindex(years), US_BASE_YEAR
    ).reindex(years)
else:
    df["us_software_index"] = float("nan")

log.warning("us_software_index will be null for some years")


def test(df):
    df = df.reset_index()
    log.info("master dataset:\n%s", df.to_string(index=False))

    assert len(df) == 11, f"expected 11 years, got {len(df)}"

    # grad index should be higher in 2024 than 2015
    assert (
        df.loc[df["year"] == 2024, "au_grad_index"].values[0] > 150
    ), "grad index should be well above 100 by 2024"

    # ict vacancy index should be below 100 by 2024 (below 2015 baseline)
    assert (
        df.loc[df["year"] == 2024, "au_ict_index"].values[0] < 100
    ), "ict vacancy index should be below 2015 baseline by 2024"

    # us data should be null before 2020
    pre2020_us = df.loc[df["year"] < 2020, "us_software_index"]
    if not us_software.empty:
        assert pre2020_us.isna().all(), "us data should be null before 2020"

    log.info("all checks passed")


test(df)

df.to_csv(f"{OUTPUT}", index=False)
log.info(f"saved to {OUTPUT}")
