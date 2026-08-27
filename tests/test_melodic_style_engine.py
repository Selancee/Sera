from backend.generation.musicality.melodic_style_engine import build_melodic_style_profile, generate_phrase_degree_labels
from backend.generation.seed_service import make_seeded_rng


def test_chinese_profile_uses_pentatonic_labels() -> None:
    profile = build_melodic_style_profile({"base_style": "chinese", "custom_style_tags": ["chinese"]}, "C major", "major", "intermediate")
    labels = generate_phrase_degree_labels(profile, "opening", 12, make_seeded_rng(123, "melody"))

    assert profile["pitch_vocabulary"] == "pentatonic"
    assert set(labels).issubset({"1", "2", "3", "5", "6"})


def test_anime_and_cyberpunk_profiles_have_distinct_contours() -> None:
    anime = build_melodic_style_profile({"custom_style_tags": ["anime"], "base_style": "pop"}, "C major", "major", "intermediate")
    cyberpunk = build_melodic_style_profile({"custom_style_tags": ["cyberpunk"], "base_style": "electronic"}, "A minor", "minor", "intermediate")

    assert anime["contour_policy"] == "lyrical_arch"
    assert cyberpunk["contour_policy"] == "short_cell_repetition"
    assert anime["degree_vocabulary"] != cyberpunk["degree_vocabulary"]


def test_romantic_profile_uses_long_arch() -> None:
    profile = build_melodic_style_profile({"base_style": "romantic"}, "C major", "major", "intermediate")

    assert profile["pitch_vocabulary"] == "tonal_with_neighbor_tones"
    assert profile["contour_policy"] == "long_arch"
