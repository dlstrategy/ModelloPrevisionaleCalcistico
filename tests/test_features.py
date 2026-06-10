from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.features.team_strength import compute_team_strengths


def test_team_strength_positive_values():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    finished = dataset.finished_before(dataset.matches[-1].starting_at)
    as_of = finished[-1].starting_at
    strength = compute_team_strengths(dataset, team_id=1, as_of=as_of, settings=settings)
    assert strength.attack > 0
    assert strength.defense > 0
