"""Chequeos fail-closed de tools/kaggle_kernel.py antes del push (sin red)."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from kaggle_kernel import validate_push


def test_owner_kernel_and_datasets_ok():
    assert validate_push("nicolasbuttaro/edgelab-x", ["nicolasbuttaro/edgelab-data-catalog"], "nicolasbuttaro") == "nicolasbuttaro"

@pytest.mark.parametrize("slug,ds", [
    ("otro/edgelab-x", []),                                            # kernel de otra cuenta
    ("nicolasbuttaro/edgelab-x", ["otro/dataset-ajeno"]),              # dataset ajeno
    ("nicolasbuttaro/Edgelab X", []),                                  # slug inválido
    ("nicolasbuttaro/edgelab-x", ["nicolasbuttaro/../holdout"]),       # ref inválida
])
def test_rejects(slug, ds):
    with pytest.raises(SystemExit):
        validate_push(slug, ds, "nicolasbuttaro")

def test_owner_from_env(monkeypatch):
    monkeypatch.setenv("EDGELAB_KAGGLE_OWNER", "gonzaloescobar")
    with pytest.raises(SystemExit):
        validate_push("nicolasbuttaro/edgelab-x", [])

def test_datasets_compartidos_por_cuentas_declaradas(monkeypatch):
    monkeypatch.setenv("EDGELAB_KAGGLE_DATASET_OWNERS", "nicolasbuttaro")
    assert validate_push("gonzaloescobar/edgelab-x", ["nicolasbuttaro/edgelab-data-catalog"], "gonzaloescobar") == "gonzaloescobar"
    with pytest.raises(SystemExit):
        validate_push("gonzaloescobar/edgelab-x", ["otro/dataset-ajeno"], "gonzaloescobar")
