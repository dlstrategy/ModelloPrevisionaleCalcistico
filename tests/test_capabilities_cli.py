"""Test CLI capabilities."""

import io
from contextlib import redirect_stderr, redirect_stdout

import pytest

from src.cli import main
from src.cli_capabilities import print_capabilities
from src.config import load_settings
from src.data_pipeline.sync import sync_league_data


@pytest.fixture(scope="module")
def synced():
    settings = load_settings()
    return sync_league_data(settings, 384)


@pytest.fixture(scope="module")
def settings():
    return load_settings()


def test_capabilities_cli_exit_zero(synced, settings):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = print_capabilities(settings, 384, profile="base")
    output = buf.getvalue()
    assert code == 0
    assert "Data capabilities" in output
    assert "PREDICTIONS" in output
    assert "disabled" in output
    assert "Data completeness score:" in output


def test_capabilities_module_entrypoint(synced):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(["capabilities", "--profile", "base"])
    assert code == 0
    assert "Data capabilities" in buf.getvalue()


def test_capabilities_invalid_profile_exit_one(settings):
    err = io.StringIO()
    with redirect_stderr(err):
        code = print_capabilities(settings, 384, profile="not_a_profile")
    assert code == 1
    assert "DATA_PROFILE non valido" in err.getvalue()


def test_capabilities_advanced_profile(synced, settings):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = print_capabilities(settings, 384, profile="advanced")
    output = buf.getvalue()
    assert code == 0
    assert "profile: advanced" in output
    assert "XG" in output
