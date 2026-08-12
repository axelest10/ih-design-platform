import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

SCRIPT_PATH = Path("scripts/design_validation_batch.py")
SPEC = importlib.util.spec_from_file_location("design_validation_batch", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_batch_plan_has_exactly_50_diverse_synthetic_cases():
    cases = MODULE.build_cases()

    assert len(cases) == 50
    assert len({case.title for case in cases}) == 50
    assert {case.product_slug for case in cases} == set(MODULE.PRODUCTS)
    assert {case.country for case in cases} == {item[0] for item in MODULE.COUNTRIES}
    assert {case.format for case in cases} == set(MODULE.FORMATS)
    assert {case.language for case in cases} == {"es", "en"}
    assert {case.copy_length for case in cases} == {"short", "medium", "long"}
    assert any(case.additional_logo_keys for case in cases)
    assert any(not case.additional_logo_keys for case in cases)
    assert all(case.title.startswith("[TEST-BATCH-50 ") for case in cases)
    assert all(case.brief_payload()["constraints"]["synthetic"] for case in cases)


def test_batch_dry_run_never_logs_in_or_uses_network(capsys):
    with patch.object(MODULE, "authenticated_session") as authenticated:
        result = MODULE.main([])

    assert result == 0
    authenticated.assert_not_called()
    output = capsys.readouterr().out
    assert "Dry-run" in output
    assert "máximo teórico de llamadas de proveedor: 150" in output


def test_batch_requires_credentials_without_disclosing_values(monkeypatch, capsys):
    monkeypatch.delenv("IH_DESIGN_USERNAME", raising=False)
    monkeypatch.delenv("IH_DESIGN_PASSWORD", raising=False)

    result = MODULE.main(["--execute"])

    assert result == 2
    error = capsys.readouterr().err
    assert "IH_DESIGN_USERNAME/IH_DESIGN_PASSWORD" in error


def test_every_case_uses_an_official_primary_logo_mapping():
    allowed = {logo for _country, logos in MODULE.COUNTRIES for logo in logos}

    assert {case.brand_logo_key for case in MODULE.build_cases()} <= allowed
