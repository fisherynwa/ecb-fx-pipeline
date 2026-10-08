"""Dashboard for the ECB pipeline. It reads the GOLD tables only.

Run (from the project folder):  uv run streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

# Make the project folder importable, so the app can reuse pipeline/config.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import data  # imported after the sys.path line above, on purpose
from pipeline.config import load_config

# One fixed colour per currency, in the order of config.yaml. The colour follows
# the currency everywhere on the page. Light and dark mode each have their own
# steps of the same eight hues, checked for colour-blind readers.
PALETTE = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
              "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    "dark": ["#3987e5", "#d95926", "#199e70", "#c98500",
             "#d55181", "#008300", "#9085e9", "#e66767"],
}  # fmt: skip
MUTED = "#898781"  # axis and helper lines

st.set_page_config(page_title="ECB exchange rates", page_icon="💶", layout="wide")
cfg = load_config()


# Cache: read the database once, then reuse the result for 5 minutes. Every click
# re-runs this script from the top; without the cache, every click would query DuckDB.
@st.cache_data(ttl=300)
def load(db_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    return data.load_daily(Path(db_path)), data.load_monthly(Path(db_path))


if not cfg.database.exists():
    st.error(f"No database at `{cfg.database}`. Run the pipeline first.")
    st.stop()
try:
    daily, monthly = load(str(cfg.database))
except duckdb.CatalogException:
    st.error(
        "The gold tables don't exist yet. Run `dbt build` in the dbt folder first."
    )
    st.stop()
except duckdb.IOException:
    st.warning("The database is busy, probably because the pipeline is writing to it. "
               "Try again in a minute.")  # fmt: skip
    st.stop()

# Currencies in config order first, then any others found in the data
currencies = [c for c in cfg.currencies if c in set(daily["currency"])]
currencies += sorted(set(daily["currency"]) - set(currencies))
mode = st.context.theme.type or "light"
colors = {c: PALETTE[mode][i % 8] for i, c in enumerate(currencies)}


def line_chart(df: pd.DataFrame, y: str, y_title: str, fmt: str) -> alt.LayerChart:
    """Lines per currency, with a hover line and a tooltip for the nearest day."""
    shown = [c for c in currencies if c in set(df["currency"])]
    color = alt.Color(
        "currency:N",
        scale=alt.Scale(domain=shown, range=[colors[c] for c in shown]),
        legend=alt.Legend(orient="top", title=None) if len(shown) > 1 else None,
    )
    base = alt.Chart(df).encode(
        x=alt.X("rate_date:T", title=None),
        # zero=False: exchange rates move by a few %, a zero baseline would flatten them
        y=alt.Y(f"{y}:Q", title=y_title, scale=alt.Scale(zero=False)),
        color=color,
    )
    hover = alt.selection_point(
        fields=["rate_date"], nearest=True, on="pointerover", empty=False
    )
    lines = base.mark_line(strokeWidth=2)
    points = (
        base.mark_point(size=70, filled=True)
        .encode(
            opacity=alt.when(hover).then(alt.value(1)).otherwise(alt.value(0)),
            tooltip=[
                alt.Tooltip("rate_date:T", title="Date", format="%d %b %Y"),
                alt.Tooltip("currency:N", title="Currency"),
                alt.Tooltip(f"{y}:Q", title=y_title, format=fmt),
            ],
        )
        .add_params(hover)
    )
    rule = (
        alt.Chart(df)
        .mark_rule(color=MUTED, strokeWidth=1)
        .encode(x="rate_date:T")
        .transform_filter(hover)
    )
    return alt.layer(lines, rule, points).properties(height=380)


# ---------- Header ----------
latest_date = daily["rate_date"].max()
st.title("Euro reference exchange rates")
st.caption(
    f"ECB daily reference rates · data up to {latest_date:%d %B %Y} · "
    f"{len(currencies)} currencies · source table: gold.fx_daily"
)

# ---------- Filter, one row above the charts ----------
period = (
    st.segmented_control(
        "Period", list(data.PERIODS), default="6 months", label_visibility="collapsed"
    )
    or "6 months"
)
shown = data.filter_period(daily, period)

# ---------- Latest rate per currency ----------
latest = data.latest_per_currency(daily)
for col, cur in zip(st.columns(len(currencies)), currencies, strict=True):
    row = latest.loc[cur]
    recent = daily.loc[daily["currency"] == cur, "units_per_eur"].tail(60)
    col.metric(
        f"1 EUR in {cur}",
        f"{row['units_per_eur']:.4f}",
        delta=None if pd.isna(row["daily_return"]) else f"{row['daily_return']:+.2%}",
        delta_color="off",  # a rising rate is not "good" or "bad", so no green/red
        chart_data=recent.tolist(),
        chart_type="line",
        border=True,
    )

# ---------- Charts ----------
tab_rate, tab_compare, tab_vol, tab_month = st.tabs(
    ["Rate", "Compare", "Volatility", "Monthly"]
)

with tab_rate:
    cur = st.selectbox("Currency", currencies)
    one = shown[shown["currency"] == cur]
    st.altair_chart(line_chart(one, "units_per_eur", f"{cur} per EUR", ".4f"))

with tab_compare:
    rebased = data.rebase_to_100(shown)
    st.altair_chart(line_chart(rebased, "index_100", "Index, first day = 100", ".2f"))
    st.caption(
        "Each currency starts at 100, so currencies with very different rates fit "
        "on one axis. Above 100: one euro buys more of that currency than at the start."
    )
    with st.expander("Show the data"):
        wide = rebased.pivot(index="rate_date", columns="currency", values="index_100")
        st.dataframe(wide[[c for c in currencies if c in wide]].round(2))

with tab_vol:
    vol = shown.dropna(subset=["volatility_20d"]).assign(
        volatility_pct=lambda d: d["volatility_20d"] * 100
    )
    st.altair_chart(line_chart(vol, "volatility_pct", "Volatility, % per year", ".1f"))
    st.caption(
        "Standard deviation of the last 20 daily log returns, scaled to a year. "
        "Empty for each currency's first 20 days, until a full window exists."
    )
    with st.expander("Show the data"):
        wide = vol.pivot(index="rate_date", columns="currency", values="volatility_pct")
        st.dataframe(wide[[c for c in currencies if c in wide]].round(2))

with tab_month:
    st.dataframe(
        monthly,
        hide_index=True,
        column_config={
            "month": st.column_config.DateColumn("Month", format="MMM YYYY"),
            "currency": "Currency",
            "n_days": "Days",
            "avg_rate": st.column_config.NumberColumn("Average", format="%.4f"),
            "min_rate": st.column_config.NumberColumn("Min", format="%.4f"),
            "max_rate": st.column_config.NumberColumn("Max", format="%.4f"),
            "month_end_rate": st.column_config.NumberColumn("Month end", format="%.4f"),
        },
    )
