import pytest

from app import scoring


def metrics(**overrides):
    m = {
        "ndvi_before": 0.7, "ndvi_now": 0.25, "ndvi_loss": 0.6,
        "water_before": 0.02, "water_now": 0.85, "flood_fraction": 0.8,
        "before_image_date": "2019-07-31", "now_image_date": "2019-08-15",
        "before_clear": 0.94, "now_clear": 0.88, "days_between": 15,
    }
    m.update(overrides)
    return m


# --- crop health loss -----------------------------------------------------------------


def test_ndvi_loss_is_share_of_last_weeks_crop_health_gone_now():
    assert scoring.ndvi_loss(0.2, 0.8) == pytest.approx(0.75)
    assert scoring.ndvi_loss(0.5, 0.3) == 0           # greener than before: no loss
    assert scoring.ndvi_loss(0.0, 0.05) == pytest.approx(0.5)  # tiny "before" uses 0.1
    assert scoring.ndvi_loss(None, 0.5) is None


# --- damage score and level --------------------------------------------------------------


def test_flood_score_weights_new_water_and_crop_health_equally():
    score, missing = scoring.damage_score("flood", {"flood_fraction": 0.8, "ndvi_loss": 0.6})
    assert score == 70 and missing == []


def test_drought_and_other_use_crop_health_only():
    assert scoring.damage_score("drought", {"ndvi_loss": 0.42, "flood_fraction": 1.0})[0] == 42
    assert scoring.damage_score("other", {"ndvi_loss": 0.3})[0] == 30


def test_missing_component_rescales_and_is_reported():
    score, missing = scoring.damage_score("flood", {"flood_fraction": None, "ndvi_loss": 0.6})
    assert score == 60 and missing == ["flood_fraction"]
    assert scoring.damage_score("flood", {})[0] is None
    assert scoring.damage_level(None) == "unknown"


@pytest.mark.parametrize("score, level", [(0, "none"), (14, "none"), (15, "low"), (35, "moderate"), (59, "moderate"), (60, "severe")])
def test_damage_levels(score, level):
    assert scoring.damage_level(score) == level


# --- confidence -----------------------------------------------------------------------------


def test_high_confidence_with_two_clear_images_close_together():
    result = scoring.confidence("flood", metrics(), area_pixels=102)
    assert result["level"] == "high"
    assert "Clear Sentinel-2 image 1 week before: 2019-07-31" in result["reasons"]
    assert "Clear Sentinel-2 image now: 2019-08-15" in result["reasons"]


@pytest.mark.parametrize(
    "overrides, pixels",
    [
        ({"before_image_date": None}, 102),   # no "before" image
        ({"now_image_date": None}, 102),      # no image since the event
        ({}, 8),                              # tiny plot
        ({"ndvi_before": 0.1}, 102),          # little crop to begin with
    ],
)
def test_low_confidence(overrides, pixels):
    assert scoring.confidence("flood", metrics(**overrides), area_pixels=pixels)["level"] == "low"


def test_medium_confidence_for_partly_cloudy_or_far_apart_images():
    assert scoring.confidence("flood", metrics(now_clear=0.6), area_pixels=102)["level"] == "medium"
    result = scoring.confidence("flood", metrics(days_between=30), area_pixels=102)
    assert result["level"] == "medium" and "The two images are 30 days apart" in result["reasons"]


def test_score_assessment_shape():
    result = scoring.score_assessment("flood", metrics(), area_pixels=102)
    assert result["score"] == {"damage_score": 70, "damage_level": "severe"}
    assert result["confidence"]["level"] == "high"
