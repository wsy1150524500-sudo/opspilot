from __future__ import annotations

import os
import tempfile

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from pydantic import SecretStr

from ops_agent.ai.config import load_ai_config, redact, save_ai_config
from ops_agent.ai.errors import ConfigError
from ops_agent.ai.models import AIConfig, ProviderConfig, ProviderKind


# ── Property 6: Credential redaction never leaks keys ───────────────

@given(key=st.text(min_size=8, max_size=50, alphabet=st.characters(blacklist_characters="\x00")))
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_property6_credential_redaction(key):
    cfg = ProviderConfig(
        kind=ProviderKind.OPENAI,
        api_key=SecretStr(key),
        model="test",
    )
    ai = AIConfig(provider=cfg)

    # model_dump should not contain the raw key in the api_key field
    dumped = ai.model_dump()
    api_key_val = dumped["provider"]["api_key"]
    assert api_key_val != key  # SecretStr serializes to ********

    # redact() should mask it
    redacted = redact(ai)
    assert redacted["provider"]["api_key"] == "********"

    # model_dump_json should not contain the raw key
    json_str = ai.model_dump_json()
    assert key not in json_str

    # repr should not contain raw key
    assert key not in repr(ai)


# ── Property 9: Config env substitution + base_url rule ─────────────

@given(
    env_value=st.text(min_size=1, max_size=30, alphabet=st.characters(blacklist_characters="\x00\n:")),
)
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_property9_env_substitution(env_value):
    env_name = "TEST_AI_KEY_HYPOTHESIS"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(
            f"provider:\n"
            f"  kind: openai\n"
            f"  api_key: ${{{env_name}}}\n"
            f"  model: test-model\n"
            f"max_iterations: 5\n"
        )
        f.flush()
        path = f.name

    try:
        old_val = os.environ.get(env_name)
        os.environ[env_name] = env_value
        try:
            cfg = load_ai_config(path)
            secret = cfg.provider.api_key.get_secret_value()
            assert secret == env_value
        finally:
            if old_val is None:
                del os.environ[env_name]
            else:
                os.environ[env_name] = old_val
    finally:
        os.unlink(path)


def test_compat_requires_base_url():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(
            "provider:\n"
            "  kind: openai_compatible\n"
            "  api_key: test-key\n"
            "  model: test-model\n"
            "max_iterations: 5\n"
        )
        f.flush()
        path = f.name

    try:
        with pytest.raises(ConfigError, match="base_url"):
            load_ai_config(path)
    finally:
        os.unlink(path)


def test_compat_with_base_url_works():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(
            "provider:\n"
            "  kind: openai_compatible\n"
            "  base_url: https://api.example.com/v1\n"
            "  api_key: test-key\n"
            "  model: test-model\n"
            "max_iterations: 5\n"
        )
        f.flush()
        path = f.name

    try:
        cfg = load_ai_config(path)
        assert cfg.provider.base_url == "https://api.example.com/v1"
    finally:
        os.unlink(path)


def test_load_nonexistent_raises():
    with pytest.raises(ConfigError, match="not found"):
        load_ai_config("/nonexistent/path.yaml")


def test_save_and_load_roundtrip():
    cfg = AIConfig(
        provider=ProviderConfig(
            kind=ProviderKind.OPENAI,
            api_key=SecretStr("my-secret-key"),
            model="gpt-4o",
        )
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        path = f.name

    try:
        os.environ["OPENAI_API_KEY"] = "my-secret-key"
        save_ai_config(cfg, path, store_key_as_env=True)

        loaded = load_ai_config(path)
        assert loaded.provider.api_key.get_secret_value() == "my-secret-key"
        assert loaded.provider.model == "gpt-4o"
    finally:
        os.unlink(path)
        os.environ.pop("OPENAI_API_KEY", None)
