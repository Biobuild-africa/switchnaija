import pytest

from switchnaija.report import impact_card


def test_impact_card_is_png():
    png = impact_card("Ede, Osun", "1 kWp + 3 kWh LFP", 1_500_000, 1.2, 1200, 3.1, "Battery note")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.network
def test_pvgis_live_ikeja(tmp_path, monkeypatch):
    monkeypatch.setenv("SWITCHNAIJA_CACHE", str(tmp_path))
    from switchnaija.sources.pvgis import fetch_pv_hourly
    df = fetch_pv_hourly(6.6016, 3.3516, year=2023)
    assert len(df) == 8760
    assert 1100 < df["pv_kw_per_kwp"].sum() < 1700


@pytest.mark.network
def test_nasa_power_daily_rain(tmp_path, monkeypatch):
    monkeypatch.setenv("SWITCHNAIJA_CACHE", str(tmp_path))
    from switchnaija.sources.nasa_power import fetch_daily
    df = fetch_daily(7.7333, 4.4333, start="20230101", end="20231231")
    assert len(df) == 365
    assert df["PRECTOTCORR"].sum() > 500
