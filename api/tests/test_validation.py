from datetime import date

import pytest

from app.validation import ValidationError, ring_area_m2, validate_event, validate_geometry

TODAY = date(2026, 10, 17)


# Default: the outline of sample plot plt_seed_1 (app/seed_plots.json).
def square(lng=75.0584, lat=16.7323, half_deg=0.0005):
    w, e, s, n = (round(v, 6) for v in (lng - half_deg, lng + half_deg, lat - half_deg, lat + half_deg))
    return {"type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]}


def test_area_of_a_roughly_one_hectare_square():
    # 0.001 deg x 0.001 deg at 16.7 N is about 111 m x 106 m.
    area = ring_area_m2(square()["coordinates"][0])
    assert 11_000 < area < 12_500


def test_valid_plot_passes_and_ring_is_closed():
    geometry = square()
    geometry["coordinates"][0].pop()  # unclosed ring
    clean, area_ha = validate_geometry(geometry)
    ring = clean["coordinates"][0]
    assert ring[0] == ring[-1]
    assert 1.1 < area_ha < 1.25


@pytest.mark.parametrize(
    "geometry, message",
    [
        (None, "single polygon"),
        ({"type": "Point", "coordinates": [75, 16]}, "single polygon"),
        ({"type": "Polygon", "coordinates": []}, "missing"),
        ({"type": "Polygon", "coordinates": [[["a", 1]]]}, "invalid coordinates"),
        ({"type": "Polygon", "coordinates": [[[75, 16], [75.001, 16], [75, 16]]]}, "at least 3 corners"),
        (square(lng=10.0, lat=50.0), "in India"),
        (square(half_deg=0.0001), "too small"),
        (square(half_deg=0.01), "too large"),
    ],
)
def test_invalid_geometry(geometry, message):
    with pytest.raises(ValidationError, match=message):
        validate_geometry(geometry)


def test_bow_tie_polygon_is_rejected():
    bow_tie = {
        "type": "Polygon",
        "coordinates": [[[75.0, 16.0], [75.002, 16.002], [75.002, 16.0], [75.0, 16.002], [75.0, 16.0]]],
    }
    with pytest.raises(ValidationError, match="crosses itself"):
        validate_geometry(bow_tie)


def test_event_dates():
    assert validate_event("flood", "2019-08-07", today=TODAY)[1] == date(2019, 8, 7)
    with pytest.raises(ValidationError, match="starts in 2016"):
        validate_event("flood", "2015-12-31", today=TODAY)
    with pytest.raises(ValidationError, match="before today"):
        validate_event("flood", "2026-10-17", today=TODAY)
    with pytest.raises(ValidationError, match="YYYY-MM-DD"):
        validate_event("flood", "07/08/2019", today=TODAY)
    with pytest.raises(ValidationError, match="event type"):
        validate_event("earthquake", "2019-08-07", today=TODAY)


def test_drought_season_window():
    _, _, season = validate_event(
        "drought", "2023-08-31", {"start": "2023-06-01", "end": "2023-09-30"}, today=TODAY
    )
    assert season == {"start": "2023-06-01", "end": "2023-09-30"}
    with pytest.raises(ValidationError, match="end after it starts"):
        validate_event("drought", "2023-08-31", {"start": "2023-09-30", "end": "2023-06-01"}, today=TODAY)


def test_season_window_ignored_for_floods():
    assert validate_event("flood", "2019-08-07", {"start": "x", "end": "y"}, today=TODAY)[2] is None
