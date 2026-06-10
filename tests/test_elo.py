from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.features.match_context import build_match_context
from src.models.elo import EloModel


def test_elo_predicts_valid_probabilities():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    upcoming = [m for m in dataset.matches if not m.is_finished][0]
    model = EloModel(settings, dataset)
    context = build_match_context(dataset, upcoming, settings)
    probs = model.predict(context)
    assert abs(probs.home + probs.draw + probs.away - 1.0) < 1e-6


def test_elo_is_ready():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    assert EloModel(settings, dataset).is_ready() is True
