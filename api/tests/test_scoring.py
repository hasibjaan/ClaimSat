import pytest

from app import scoring


def good_metrics(**overrides):
    metrics = {
        "ndvi_loss": 0.6,
        "flood_fraction": 0.8,
        "rain_deficit": 0.5,
        "crop_fraction": 0.8,
        "clear_obs_before": 3,
        "clear_obs_after": 4,
        "radar_obs_pre": 2,
        "radar_obs_post": 1,
    }
    metrics.update(overrides)
    return metrics


# --- ndvi_loss / rain_deficit -----------------------------------------------------


def test_ndvi_loss_is_share_of_normal_vegetation_missing():
    assert scoring.ndvi_loss(0.2, 0.8) == pytest.approx(0.75)


def test_ndvi_loss_is_zero_when_crop_is_as_healthy_as_usual():
    # A normal harvest lowers NDVI in previous years too, so no loss is reported.
    assert scoring.ndvi_loss(0.3, 0.3) == 0
    assert scoring.ndvi_loss(0.5, 0.3) == 0  # healthier than usual is clamped to 0


def test_ndvi_loss_guards_against_tiny_baselines():
    # Baseline below 0.1 uses 0.1 as the denominator, so bare land doesn't explode.
    assert scoring.ndvi_loss(0.0, 0.05) == pytest.approx(0.5)


def test_ndvi_loss_missing_data():
    assert scoring.ndvi_loss(None, 0.5) is None
    assert scoring.ndvi_loss(0.5, None) is None


def test_rain_deficit():
    assert scoring.rain_deficit(300, 600) == pytest.approx(0.5)
    assert scoring.rain_deficit(700, 600) == 0
    assert scoring.rain_deficit(None, 600) is None
    assert scoring.rain_deficit(300, 0) is None


# --- damage score and level -------------------------------------------------------


def test_flood_score_weights_flood_extent_and_vegetation_loss_equally():
    score, missing = scoring.damage_score("flood", {"flood_fraction": 0.8, "ndvi_loss": 0.6})
    assert score == 70
    assert missing == []


def test_drought_score_weights():
    score, _ = scoring.damage_score("drought", {"ndvi_loss": 0.5, "rain_deficit": 1.0})
    assert score == 70  # 100 * (0.6 * 0.5 + 0.4 * 1.0)


def test_other_score_is_vegetation_loss_only():
    score, _ = scoring.damage_score("other", {"ndvi_loss": 0.42, "flood_fraction": 1.0})
    assert score == 42


def test_missing_component_rescales_weights_and_is_reported():
    score, missing = scoring.damage_score("flood", {"flood_fraction": None, "ndvi_loss": 0.6})
    assert score == 60
    assert missing == ["flood_fraction"]


def test_no_data_gives_no_score():
    score, missing = scoring.damage_score("flood", {"flood_fraction": None, "ndvi_loss": None})
    assert score is None
    assert scoring.damage_level(score) == "unknown"
    assert missing == ["flood_fraction", "ndvi_loss"]


@pytest.mark.parametrize(
    "score, level",
    [(0, "none"), (14, "none"), (15, "low"), (34, "low"), (35, "moderate"), (59, "moderate"), (60, "severe"), (100, "severe")],
)
def test_damage_level_thresholds(score, level):
    assert scoring.damage_level(score) == level


# --- confidence -------------------------------------------------------------------


def test_high_confidence_when_everything_is_available():
    result = scoring.confidence("flood", good_metrics(), area_pixels=102)
    assert result["level"] == "high"
    assert "Radar images available before and after the event" in result["reasons"]
    assert "Plot is 80% cropland" in result["reasons"]


def test_flood_without_radar_is_not_high():
    result = scoring.confidence("flood", good_metrics(radar_obs_post=0), area_pixels=102)
    assert result["level"] == "medium"


def test_flood_with_no_clear_optical_but_radar_is_medium():
    # Monsoon clouds: radar still sees the flood, so not low.
    result = scoring.confidence("flood", good_metrics(clear_obs_after=0), area_pixels=102)
    assert result["level"] == "medium"


def test_flood_with_no_optical_and_no_radar_is_low():
    metrics = good_metrics(clear_obs_after=0, radar_obs_post=0)
    assert scoring.confidence("flood", metrics, area_pixels=102)["level"] == "low"


def test_drought_with_no_clear_images_is_low():
    metrics = good_metrics(clear_obs_before=0, radar_obs_pre=None, radar_obs_post=None)
    assert scoring.confidence("drought", metrics, area_pixels=102)["level"] == "low"


def test_drought_ignores_radar():
    metrics = good_metrics(radar_obs_pre=None, radar_obs_post=None)
    assert scoring.confidence("drought", metrics, area_pixels=102)["level"] == "high"


def test_not_cropland_is_low():
    assert scoring.confidence("flood", good_metrics(crop_fraction=0.2), area_pixels=102)["level"] == "low"


def test_unknown_cropland_is_not_high():
    assert scoring.confidence("flood", good_metrics(crop_fraction=None), area_pixels=102)["level"] == "medium"


def test_tiny_plot_is_low_and_small_plot_is_medium():
    assert scoring.confidence("flood", good_metrics(), area_pixels=8)["level"] == "low"
    assert scoring.confidence("flood", good_metrics(), area_pixels=15)["level"] == "medium"


def test_partial_score_is_not_high_and_says_why():
    result = scoring.confidence("flood", good_metrics(), area_pixels=102, missing_components=["flood_fraction"])
    assert result["level"] == "medium"
    assert "Score uses partial data: no flood extent measurement" in result["reasons"]


def test_score_assessment_shape():
    result = scoring.score_assessment("flood", good_metrics(), area_pixels=102)
    assert result["score"] == {"damage_score": 70, "damage_level": "severe"}
    assert result["confidence"]["level"] == "high"
