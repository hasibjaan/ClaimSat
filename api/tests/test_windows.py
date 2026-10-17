"""Date windows and NDVI series shaping (pure Python, no Earth Engine)."""

from datetime import date, datetime, timezone

from app import ee_analysis

TODAY = date(2026, 10, 17)


def ms(iso, hour=5):
    return int(datetime.fromisoformat(iso).replace(hour=hour, tzinfo=timezone.utc).timestamp() * 1000)


def test_flood_windows():
    w = ee_analysis.build_windows("flood", date(2019, 8, 7), today=TODAY)
    assert w["before"] == {"start": "2019-07-08", "end": "2019-08-06"}
    assert w["after"] == {"start": "2019-08-12", "end": "2019-09-06"}
    assert w["radar_pre"] == {"start": "2019-07-08", "end": "2019-08-06"}
    assert w["radar_post"] == {"start": "2019-08-07", "end": "2019-08-17"}
    assert w["series"] == {"start": "2019-05-09", "end": "2019-10-06"}
    assert w["baseline_years"] == [2016, 2017, 2018]


def test_other_event_has_no_radar_windows():
    w = ee_analysis.build_windows("other", date(2019, 8, 7), today=TODAY)
    assert "radar_pre" not in w and "after" in w


def test_drought_default_season():
    w = ee_analysis.build_windows("drought", date(2023, 8, 31), today=TODAY)
    assert w["after"] == {"start": "2023-06-01", "end": "2023-09-30"}
    assert w["before"] == {"start": "2023-05-02", "end": "2023-05-31"}


def test_drought_custom_season():
    season = {"start": "2023-07-01", "end": "2023-10-15"}
    w = ee_analysis.build_windows("drought", date(2023, 8, 31), season_window=season, today=TODAY)
    assert w["after"] == season


def test_windows_are_clipped_to_today():
    w = ee_analysis.build_windows("flood", date(2026, 10, 10), today=TODAY)
    assert w["after"]["end"] == "2026-10-17"
    assert w["radar_post"]["end"] == "2026-10-17"


def test_shift_years_handles_leap_day():
    assert ee_analysis.shift_years(date(2020, 2, 29), -1) == date(2019, 2, 28)
    assert ee_analysis.shift_years(date(2019, 8, 7), -3) == date(2016, 8, 7)


def test_unique_dates_collapses_tiles_from_the_same_day():
    stamps = [ms("2019-08-18", 5), ms("2019-08-18", 6), ms("2019-08-23")]
    assert ee_analysis.unique_dates(stamps) == ["2019-08-18", "2019-08-23"]


def test_build_series_averages_same_day_and_bins_baseline():
    event = date(2019, 8, 7)
    this_year = ([ms("2019-08-18", 5), ms("2019-08-18", 6)], [0.2, 0.4])
    baseline = {
        1: ([ms("2018-08-17")], [0.6]),  # offset +10
        2: ([ms("2017-08-19")], [0.8]),  # offset +12 -> same 10-day bin
    }
    series = ee_analysis.build_series(event, this_year, baseline)
    assert series["this_year"] == [{"day_offset": 11, "date": "2019-08-18", "ndvi": 0.3}]
    assert series["baseline"] == [{"day_offset": 10, "ndvi": 0.7}]
