"""CLI principale."""

from __future__ import annotations

import argparse
import json
import sys

from src.backtesting.ablation import run_ablation_study, save_ablation_report
from src.backtesting.backtest import run_backtest, run_backtest_all_models
from src.backtesting.reports import save_comparison_report
from src.backtesting.walk_forward import run_walk_forward, save_walk_forward_report
from src.backtesting.walk_forward_trained import run_walk_forward_refit
from src.cli_capabilities import print_capabilities
from src.cli_status import print_status
from src.cli_train import print_train
from src.cli_validate import print_validate
from src.config import BACKTESTS_DIR, SERIE_A_LEAGUE_ID, load_settings
from src.data_pipeline.sync import load_dataset, sync_league_data
from src.features.feature_vector import summarize_feature_groups
from src.features.match_context import build_match_context
from src.logging_config import setup_logging
from src.models.registry import MODEL_NAMES, get_model_by_name
from src.prediction.explain import explain_prediction
from src.prediction.predict_round import default_output_path, predict_round, save_predictions


def _resolve_model(settings, dataset, name: str):
    return get_model_by_name(name, settings, dataset)


def cmd_validate(args: argparse.Namespace) -> int:
    settings = load_settings()
    setup_logging(settings.log_level)
    league_id = args.league or settings.default_league_id
    return print_validate(settings, league_id, profile=args.profile)


def cmd_capabilities(args: argparse.Namespace) -> int:
    settings = load_settings()
    setup_logging(settings.log_level)
    league_id = args.league or settings.default_league_id
    return print_capabilities(settings, league_id, profile=args.profile)


def cmd_walk_forward(args: argparse.Namespace) -> int:
    settings = load_settings()
    setup_logging(settings.log_level)
    league_id = args.league or settings.default_league_id
    model_name = args.model or "ensemble"
    dataset = load_dataset(settings, league_id)

    if model_name == "feature_trained":
        report = run_walk_forward_refit(
            dataset,
            settings,
            profile=args.profile,
            min_train_matches=args.min_train_matches,
            test_window_size=args.test_window_size,
            step_size=args.step_size,
        )
    else:
        model = _resolve_model(settings, dataset, model_name)
        report = run_walk_forward(
            dataset,
            model,
            settings,
            min_train_matches=args.min_train_matches,
            test_window_size=args.test_window_size,
            step_size=args.step_size,
        )
    json_path, csv_path = save_walk_forward_report(report, BACKTESTS_DIR)

    m = report.aggregate_metrics
    print(f"Walk-forward backtest — league {league_id}, model {model_name}")
    print(f"Training mode: {report.training_mode}")
    if report.data_profile:
        print(f"Data profile: {report.data_profile}")
    print(f"Train iniziale: {report.min_train_matches}")
    print(f"Test window: {report.test_window_size}")
    print(f"Step: {report.step_size}")
    print()
    print(f"Windows: {len(report.windows)}")
    print(f"Partite testate: {report.total_tested_matches}")
    print()
    print("Aggregate:")
    print(f"  Accuracy:    {m.accuracy:.3f}")
    print(f"  Brier score: {m.brier_score:.4f}")
    print(f"  Log-loss:    {m.log_loss:.4f}")
    print(f"  Brier skill: {m.brier_skill_score:.4f}")
    print(f"  Cal gap:     {m.mean_calibration_gap:.4f}")
    print(f"  Pick over:   {m.pick_overconfidence_rate:.3f}")
    print(f"  Pick under:  {m.pick_underconfidence_rate:.3f}")
    print()
    print(f"Report JSON: {json_path}")
    print(f"Report CSV:  {csv_path}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    settings = load_settings()
    setup_logging(settings.log_level)
    league_id = args.league or settings.default_league_id
    return print_status(settings, league_id)


def cmd_train(args: argparse.Namespace) -> int:
    settings = load_settings()
    setup_logging(settings.log_level)
    league_id = args.league or settings.default_league_id
    return print_train(
        settings,
        league_id,
        model_name=args.model,
        profile=args.profile,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
        min_samples=args.min_samples,
    )


def cmd_sync(args: argparse.Namespace) -> int:
    settings = load_settings()
    setup_logging(settings.log_level)
    league_id = args.league or settings.default_league_id

    if settings.can_sync_api:
        mode = "API Sportmonks (Fase 3)"
    else:
        mode = "offline fixture (Fase 2)"

    dataset = sync_league_data(settings, league_id)
    print(f"Sync OK [{mode}] — lega {league_id}, partite: {len(dataset.matches)}")
    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    settings = load_settings()
    setup_logging(settings.log_level)
    league_id = args.league or settings.default_league_id
    dataset = load_dataset(settings, league_id)
    model_name = args.model or "ensemble"
    model = _resolve_model(settings, dataset, model_name)
    if not model.is_ready():
        print(
            f"Modello {model_name} non pronto. "
            f"Esegui: python -m src.cli train --league {league_id} --model feature_trained",
            file=sys.stderr,
        )
        return 1

    if args.date:
        matches = dataset.upcoming_on(args.date)
        if not matches:
            matches = [
                m
                for m in dataset.matches
                if m.starting_at.strftime("%Y-%m-%d") == args.date and not m.is_finished
            ]
    else:
        print("Specifica --date YYYY-MM-DD", file=sys.stderr)
        return 1

    if not matches:
        print(f"Nessuna partita trovata per {args.date}")
        return 0

    predictions = predict_round(dataset, matches, model, settings)
    output = default_output_path(args.date)
    save_predictions(predictions, output)

    print(f"Modello: {model_name}")
    print(f"{'Partita':<35} {'P(1)':>6} {'P(X)':>6} {'P(2)':>6} {'Pick':>5} {'Conf':>6}")
    print("-" * 70)
    for p in predictions:
        probs = p.probabilities
        label = f"{p.home_team} vs {p.away_team}"
        uncertain = " *" if p.metadata.get("uncertain") else ""
        print(
            f"{label:<35} {probs.home:>5.1%} {probs.draw:>5.1%} {probs.away:>5.1%} "
            f"{p.pick.value:>5} {p.confidence:>5.1%}{uncertain}"
        )

    if args.explain and predictions:
        profile = getattr(model, "data_profile", None)
        for match, pred in zip(matches, predictions):
            ctx = build_match_context(
                dataset,
                match,
                settings,
                profile=profile,
            )
            explanation = explain_prediction(ctx, pred, dataset=dataset, settings=settings)
            print(f"\nExplain — {pred.home_team} vs {pred.away_team}:")
            print(json.dumps(explanation, indent=2))

    print(f"\nSalvato: {output}")
    return 0


def cmd_features(args: argparse.Namespace) -> int:
    settings = load_settings()
    setup_logging(settings.log_level)
    league_id = args.league or settings.default_league_id
    dataset = load_dataset(settings, league_id)

    sample = next((m for m in dataset.matches if not m.is_finished), dataset.matches[0])
    ctx = build_match_context(dataset, sample, settings)

    summary = summarize_feature_groups(ctx.feature_vector)
    print(f"Feature engineering — lega {league_id}")
    print(f"Partita esempio: {sample.home.team_name} vs {sample.away.team_name} (id={sample.id})")
    print(f"Feature attive: {len(ctx.feature_vector)}")
    print("\nGruppi:")
    for group, count in sorted(summary.items()):
        print(f"  {group:<22} {count:>3} feature")
    print("\nFeature vector (prime 20 per modulo):")
    for key in sorted(ctx.feature_vector.keys())[:20]:
        print(f"  {key:<40} {ctx.feature_vector[key]:.4f}")
    if len(ctx.feature_vector) > 20:
        print(f"  ... +{len(ctx.feature_vector) - 20} altre")
    return 0


def cmd_ablation(args: argparse.Namespace) -> int:
    settings = load_settings()
    setup_logging(settings.log_level)
    league_id = args.league or settings.default_league_id
    dataset = load_dataset(settings, league_id)
    max_matches = args.rounds * 10 if args.rounds else None

    results = run_ablation_study(dataset, settings, max_matches=max_matches)
    report_path = save_ablation_report(results, BACKTESTS_DIR)

    print(f"Ablation study — lega {league_id}, campioni max {max_matches or 'all'}")
    print(
        f"{'Variante':<22} {'Feat':>5} {'Acc':>6} {'Brier':>7} {'LogLoss':>8} "
        f"{'BSS':>7} {'CalGap':>7} {'PickOver':>9} {'PickUnder':>10}"
    )
    print("-" * 92)
    for r in results:
        m = r.metrics
        print(
            f"{r.variant:<22} {r.feature_count:>5} {m.accuracy:>5.1%} "
            f"{m.brier_score:>7.4f} {m.log_loss:>8.4f} {m.brier_skill_score:>7.3f} "
            f"{m.mean_calibration_gap:>7.3f} "
            f"{m.pick_overconfidence_rate:>8.1%} {m.pick_underconfidence_rate:>9.1%}"
        )
    print(f"\nReport: {report_path}")
    return 0


def cmd_backtest(args: argparse.Namespace) -> int:
    settings = load_settings()
    setup_logging(settings.log_level)
    league_id = args.league or settings.default_league_id
    dataset = load_dataset(settings, league_id)
    max_matches = args.rounds * 10 if args.rounds else None

    if args.all_models:
        results = run_backtest_all_models(dataset, settings, max_matches=max_matches)
        comparison = save_comparison_report(results, BACKTESTS_DIR)
        print("Confronto modelli (ordinati per Brier score):")
        for r in sorted(results, key=lambda x: x.metrics.brier_score):
            m = r.metrics
            print(
                f"  {r.model_name:<14} acc={m.accuracy:.3f}  "
                f"brier={m.brier_score:.4f}  logloss={m.log_loss:.4f}"
            )
        print(f"Report confronto: {comparison}")
        return 0

    model_name = args.model or "ensemble"
    model = _resolve_model(settings, dataset, model_name)
    if not model.is_ready():
        print(
            f"Modello {model_name} non pronto. "
            f"Esegui: python -m src.cli train --league {league_id} --model feature_trained",
            file=sys.stderr,
        )
        return 1
    result = run_backtest(dataset, model, settings, max_matches=max_matches)
    from src.backtesting.backtest import save_report

    json_path, csv_path = save_report(result, BACKTESTS_DIR)
    m = result.metrics
    print(f"Backtest — modello: {result.model_name}, campioni: {m.samples}")
    if result.evaluation_mode == "in_sample_artifact":
        print("Evaluation mode: in_sample_artifact")
        print(
            "WARNING: feature_trained artifact was evaluated on historical matches "
            "that may overlap with training data."
        )
        print("Use walk-forward refit for honest temporal evaluation.")
    print(f"  Accuracy:    {m.accuracy:.3f}")
    print(f"  Brier score: {m.brier_score:.4f}")
    print(f"  Log-loss:    {m.log_loss:.4f}")
    print(f"  Brier skill: {m.brier_skill_score:.4f}")
    print(f"  Cal gap:     {m.mean_calibration_gap:.4f} (media |conf-hit| sui bin)")
    print(
        f"  Pick over:   {m.pick_overconfidence_rate:.3f} "
        "(confidence pick > hit binario + margin)"
    )
    print(
        f"  Pick under:  {m.pick_underconfidence_rate:.3f} "
        "(confidence pick < hit binario - margin)"
    )
    if m.calibration_bins:
        print("  Calibrazione (confidence vs hit rate):")
        for b in m.calibration_bins:
            print(
                f"    conf={b['avg_confidence']:.2f} hit={b['hit_rate']:.2f} "
                f"n={int(b['count'])} gap={b['gap']:.2f}"
            )
    print(f"Report JSON: {json_path}")
    print(f"Report CSV:  {csv_path}")
    return 0


def cmd_transfer_estimate(args: argparse.Namespace) -> int:
    from src.players.player_value import resolve_player_value_for_league

    result = resolve_player_value_for_league(
        args.player_id,
        args.target_league,
        target_matches_played=args.target_matches,
        role=args.role,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Player {result['player_id']} -> league {result['target_league_id']}")
        print(f"  Rating:     {result['rating']:.4f}")
        print(f"  Confidence: {result['confidence']:.4f}")
        print(f"  Adapter:    {result['source']}")
        if result.get("specialist_key"):
            print(f"  Specialist: {result['specialist_key']}")
        if result.get("source_league_id") is not None:
            print(f"  Source league: {result['source_league_id']}")
        if result.get("notes"):
            print(f"  Notes: {', '.join(result['notes'])}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Motore previsionale calcistico 1/X/2 — Serie A"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sync_p = sub.add_parser("sync", help="Sync dati (offline Fase 2 o API Fase 3)")
    sync_p.add_argument("--league", type=int, default=SERIE_A_LEAGUE_ID)
    sync_p.set_defaults(func=cmd_sync)

    predict_p = sub.add_parser("predict", help="Predizioni per data")
    predict_p.add_argument("--date", required=True, help="YYYY-MM-DD")
    predict_p.add_argument("--league", type=int, default=None)
    predict_p.add_argument(
        "--model",
        choices=list(MODEL_NAMES),
        default="ensemble",
    )
    predict_p.add_argument(
        "--explain",
        action="store_true",
        help="Mostra explain JSON per ogni partita predetta",
    )
    predict_p.set_defaults(func=cmd_predict)

    backtest_p = sub.add_parser("backtest", help="Backtest senza data leakage")
    backtest_p.add_argument("--league", type=int, default=None)
    backtest_p.add_argument("--rounds", type=int, default=5)
    backtest_p.add_argument(
        "--model",
        choices=list(MODEL_NAMES),
        default="ensemble",
    )
    backtest_p.add_argument("--all-models", action="store_true", help="Confronta tutti i modelli")
    backtest_p.set_defaults(func=cmd_backtest)

    features_p = sub.add_parser("features", help="Mostra feature engineering per lega")
    features_p.add_argument("--league", type=int, default=None)
    features_p.set_defaults(func=cmd_features)

    ablation_p = sub.add_parser("ablation", help="Ablation test gruppi feature")
    ablation_p.add_argument("--league", type=int, default=None)
    ablation_p.add_argument("--rounds", type=int, default=5)
    ablation_p.set_defaults(func=cmd_ablation)

    status_p = sub.add_parser("status", help="Stato dataset, fixture companion e feature")
    status_p.add_argument("--league", type=int, default=None)
    status_p.set_defaults(func=cmd_status)

    validate_p = sub.add_parser("validate", help="Controlli data quality su dataset e fixture")
    validate_p.add_argument("--league", type=int, default=None)
    validate_p.add_argument(
        "--profile",
        choices=["base", "advanced", "all_in_no_predictions"],
        default=None,
        help="Profilo dati (default: DATA_PROFILE da .env)",
    )
    validate_p.set_defaults(func=cmd_validate)

    cap_p = sub.add_parser("capabilities", help="Capability dati e completeness per profilo")
    cap_p.add_argument("--league", type=int, default=None)
    cap_p.add_argument(
        "--profile",
        choices=["base", "advanced", "all_in_no_predictions"],
        default=None,
        help="Profilo dati (default: DATA_PROFILE da .env)",
    )
    cap_p.set_defaults(func=cmd_capabilities)

    train_p = sub.add_parser("train", help="Allenamento offline feature_trained")
    train_p.add_argument("--league", type=int, default=None)
    train_p.add_argument("--model", default="feature_trained")
    train_p.add_argument(
        "--profile",
        choices=["base", "advanced", "all_in_no_predictions"],
        default=None,
    )
    train_p.add_argument("--epochs", type=int, default=None)
    train_p.add_argument("--learning-rate", type=float, default=None)
    train_p.add_argument("--l2", type=float, default=None)
    train_p.add_argument("--min-samples", type=int, default=None)
    train_p.set_defaults(func=cmd_train)

    walk_p = sub.add_parser("walk-forward", help="Backtest walk-forward nel tempo")
    walk_p.add_argument("--league", type=int, default=None)
    walk_p.add_argument(
        "--model",
        choices=list(MODEL_NAMES),
        default="ensemble",
    )
    walk_p.add_argument(
        "--profile",
        choices=["base", "advanced", "all_in_no_predictions"],
        default=None,
        help="Profilo dati per feature_trained walk-forward refit",
    )
    walk_p.add_argument("--min-train-matches", type=int, default=10)
    walk_p.add_argument("--test-window-size", type=int, default=5)
    walk_p.add_argument("--step-size", type=int, default=5)
    walk_p.set_defaults(func=cmd_walk_forward)

    te_p = sub.add_parser(
        "transfer-estimate",
        help="Stima transfer composable giocatore (offline mock)",
    )
    te_p.add_argument("--player-id", type=int, required=True)
    te_p.add_argument("--target-league", type=int, required=True)
    te_p.add_argument("--role", default=None, help="forward, midfielder, defender, goalkeeper")
    te_p.add_argument("--target-matches", type=int, default=0)
    te_p.add_argument("--json", action="store_true", help="Output JSON")
    te_p.set_defaults(func=cmd_transfer_estimate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
