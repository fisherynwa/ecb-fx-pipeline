"""Tests for pipeline/extract.py, WITHOUT calling the real ECB API.

Tests must be fast and must not depend on the internet. So we replace
requests.get with a fake (a "mock") that returns whatever we want.
"""

import dataclasses

import pytest
import requests

from pipeline import extract


def fake_response(status_code: int, text: str = "") -> requests.Response:
    """A real Response object, filled in by hand instead of by the network."""
    response = requests.Response()
    response.status_code = status_code
    response._content = text.encode("utf-8")
    response.url = "https://example.test"
    return response


# parametrize = run the same test several times with different inputs
@pytest.mark.parametrize(
    "currencies, expected_key",
    [
        (["USD"], "D.USD.EUR.SP00.A"),
        (["USD", "GBP"], "D.USD+GBP.EUR.SP00.A"),
        (["USD", "GBP", "JPY", "CHF"], "D.USD+GBP+JPY+CHF.EUR.SP00.A"),
    ],
)
def test_build_url(cfg, currencies, expected_key):
    # a copy of the test config, with other currencies
    cfg = dataclasses.replace(cfg, currencies=currencies)
    url = extract.build_url(cfg)
    assert url == f"https://example.test/service/data/EXR/{expected_key}"


def test_fetch_rates_returns_the_csv_text(cfg, sample_csv, monkeypatch):
    # monkeypatch replaces requests.get for this test only
    response = fake_response(200, sample_csv)
    monkeypatch.setattr(extract.requests, "get", lambda *a, **k: response)
    assert extract.fetch_rates(cfg) == sample_csv


def test_fetch_rates_returns_none_when_ecb_has_no_data(cfg, monkeypatch):
    # The ECB answers 404 for "no data in this period", e.g. a weekend: not an error
    monkeypatch.setattr(extract.requests, "get", lambda *a, **k: fake_response(404))
    assert extract.fetch_rates(cfg, start="2026-10-03") is None


def test_fetch_rates_fails_loudly_on_server_error(cfg, monkeypatch):
    # A 500 is a real problem: the pipeline must stop, not continue with nothing
    monkeypatch.setattr(extract.requests, "get", lambda *a, **k: fake_response(500))
    with pytest.raises(requests.HTTPError):
        extract.fetch_rates(cfg)


def test_save_raw_keeps_the_text_exactly(cfg, sample_csv):
    # Regression test: on Windows, text-mode writing once turned "\r\n" into "\r\r\n".
    # Compare BYTES, so any change to the line endings is caught.
    path = extract.save_raw(sample_csv, cfg)
    assert path.read_bytes() == sample_csv.encode("utf-8")
