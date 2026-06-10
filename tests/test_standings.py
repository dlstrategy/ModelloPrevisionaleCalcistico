from datetime import datetime

from src.data_pipeline.sync import load_offline_dataset
from src.features.standings_features import compute_standings_table


def test_standings_table_order():
    dataset = load_offline_dataset(384)
    as_of = datetime(2025, 9, 20)
    table = compute_standings_table(dataset, as_of)
    assert 1 in table
    assert table[1].points >= table[2].points
