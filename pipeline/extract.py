"""Extract: download exchange rates from the ECB API and save the raw response.

Run:  uv run python -m pipeline.extract
"""

from datetime import datetime
from pathlib import Path

import requests

from pipeline.config import Config, load_config


def build_url(cfg: Config) -> str:
    """ECB address: base URL / dataset / series key.

    The series key has 5 parts separated by dots:
      D        daily
      USD+GBP  currencies ("+" means "and")
      EUR      quoted against the euro
      SP00     spot rate
      A        average (the official reference rate)
    """
    series_key = f"D.{'+'.join(cfg.currencies)}.EUR.SP00.A"
    return f"{cfg.base_url}/{cfg.dataset}/{series_key}"


def fetch_rates(cfg: Config, start: str | None = None) -> str | None:
    """Call the API and return the response body (CSV text).

    start: first date to fetch (YYYY-MM-DD). Default: start_period from the config.
    Returns None when the ECB has no data for that period (HTTP 404), for example
    when asking for today's rate before it is published. That is normal, not an error.
    """
    start = start or cfg.start_period
    url = build_url(cfg)
    params = {"startPeriod": start, "format": "csvdata"}

    print(f"Calling {url}  (from {start})")
    response = requests.get(url, params=params, timeout=cfg.timeout_seconds)
    # 200 = OK, 404 = no data, 500 = server error
    print(f"Status code: {response.status_code}")

    if response.status_code == 404:
        return None
    response.raise_for_status()  # stop with an error for any other problem
    return response.text


def save_raw(text: str, cfg: Config) -> Path:
    """Save exactly what the API sent, before changing anything.

    A timestamp in the file name means every run keeps its own copy.
    """
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = cfg.raw_dir / f"ecb_rates_{stamp}.csv"
    # newline="" = write the text exactly as received. Without it, Windows turns
    # every "\n" into "\r\n", so the ECB's "\r\n" line endings become "\r\r\n".
    path.write_text(text, encoding="utf-8", newline="")
    return path


if __name__ == "__main__":
    # This block runs only when the file is started directly,
    # not when another module imports its functions.
    cfg = load_config()
    text = fetch_rates(cfg)
    if text is None:
        print("No data available for this period.")
    else:
        path = save_raw(text, cfg)
        n_rows = len(text.splitlines()) - 1  # minus the header line
        print(f"Saved {n_rows} rows to {path}")
