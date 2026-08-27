from backend.generation.musicality.generation_profile import GenerationProfile
from backend.generation.musicality.texture_engine import TextureEngine


def test_texture_engine_selects_style_sensitive_texture() -> None:
    engine = TextureEngine()
    assert engine.choose_texture(GenerationProfile(style="romantic", texture="melody_accompaniment")) == "arpeggiated"
    assert engine.choose_texture(GenerationProfile(style="chinese", texture="pentatonic_open_texture")) == "pentatonic_open_texture"
