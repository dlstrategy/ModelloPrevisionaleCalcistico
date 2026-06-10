from src.config import load_settings
from src.data_pipeline.sync import load_offline_dataset
from src.models.ensemble import EnsembleModel
from src.models.poisson import PoissonModel
from src.prediction.predict_round import predict_round


def test_prediction_output_fields():
    settings = load_settings()
    dataset = load_offline_dataset(384)
    upcoming = [m for m in dataset.matches if not m.is_finished]
    model = EnsembleModel.from_settings(settings, [PoissonModel(settings)])
    predictions = predict_round(dataset, upcoming, model, settings)

    assert len(predictions) == 2
    for pred in predictions:
        assert pred.pick.value in {"1", "X", "2"}
        assert 0.0 < pred.confidence <= 1.0
        total = pred.probabilities.home + pred.probabilities.draw + pred.probabilities.away
        assert abs(total - 1.0) < 1e-6
