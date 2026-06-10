from src.config import load_settings
from src.data_pipeline.dataset_builder import MatchDataset
from src.data_pipeline.sync import load_offline_dataset
from src.domain.match import Match
from src.features.match_context import build_match_context
from src.models.poisson import PoissonModel


def test_poisson_probabilities_sum_to_one():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    upcoming = [m for m in dataset.matches if not m.is_finished][0]
    context = build_match_context(dataset, upcoming, settings)
    model = PoissonModel(settings)
    probs = model.predict(context)
    assert abs(probs.home + probs.draw + probs.away - 1.0) < 1e-6


def test_strong_home_team_favored():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    upcoming = [m for m in dataset.matches if m.id == 1006][0]
    context = build_match_context(dataset, upcoming, settings)
    model = PoissonModel(settings)
    probs = model.predict(context)
    assert probs.home >= probs.away
