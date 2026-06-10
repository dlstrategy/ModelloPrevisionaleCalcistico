from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.features.match_context import build_match_context
from src.models.registry import build_ensemble


def test_ensemble_combines_models():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    upcoming = [m for m in dataset.matches if not m.is_finished][0]
    model = build_ensemble(settings, dataset)
    context = build_match_context(dataset, upcoming, settings)
    probs = model.predict(context)
    assert abs(probs.home + probs.draw + probs.away - 1.0) < 1e-6
    assert model.name == "ensemble"
