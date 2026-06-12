"""Verifica esistenza documentazione audit logico."""

from pathlib import Path


def test_logica_funzionamento_doc_exists():
    root = Path(__file__).resolve().parent.parent
    main_doc = root / "docs" / "progetto" / "LOGICA-FUNZIONAMENTO.md"
    module_doc = root / "docs" / "progetto" / "implementazioni" / "20-logica-funzionamento-audit.md"
    assert main_doc.exists()
    assert module_doc.exists()
    assert "anti-leakage" in main_doc.read_text(encoding="utf-8").lower()
    assert "feature_trained" in main_doc.read_text(encoding="utf-8")
