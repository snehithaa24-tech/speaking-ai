from app.core.config import Settings


def test_config_debug_property():
    s = Settings(
        SECRET_KEY="test_secret_key_for_testing_purposes_only",
        GEMINI_API_KEY="test_key_for_development",
        APP_DEBUG=True,
    )
    assert s.DEBUG is True
    assert s.APP_DEBUG is True


def test_config_defaults():
    s = Settings(
        _env_file=None,
        SECRET_KEY="test_secret_key_for_testing_purposes_only",
        GEMINI_API_KEY="test_key_for_development",
    )
    assert s.APP_NAME == "SAHAYAK AI"
    assert s.GEMINI_LIVE_MODEL == "gemini-2.0-flash"
    assert s.HOST == "0.0.0.0"
    assert s.PORT == 8000

