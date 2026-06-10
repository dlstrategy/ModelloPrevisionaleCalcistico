from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.features.match_context import build_match_context
from src.models.dixon_coles import DixonColesModel
from src.models.poisson import PoissonModel


def test_dixon_coles_probabilities_sum_to_one():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    upcoming = [m for m in dataset.matches if not m.is_finished][0]
    context = build_match_context(dataset, upcoming, settings)
    probs = DixonColesModel(settings).predict(context)
    assert abs(probs.home + probs.draw + probs.away - 1.0) < 1e-6


def test_dixon_coles_differs_from_poisson_on_draw():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    upcoming = [m for m in dataset.matches if m.id == 1006][0]
    context = build_match_context(dataset, upcoming, settings)
    poisson = PoissonModel(settings).predict(context)
    dc = DixonColesModel(settings).predict(context)
    assert dc.draw != poisson.draw or dc.home != poisson.home
