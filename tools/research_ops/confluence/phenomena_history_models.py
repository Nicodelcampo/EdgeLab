"""Fixed history/representation comparisons, NOT an autonomous market runner.

Only chronological callers may fit; no calibration or scientific-plan authority
is supplied here. Equal-session training, frozen lambda, all candidates retained.
Arrays are private. Export only aggregate scores, never fitted parameters/rows.
"""
import numpy as np
from .phenomena_models import fit, predict, brier
from .phenomena_history import design, MODEL_SLICES, HISTORY_NAMES

MODELS = ("PRIOR", "HISTORY") + tuple(
    f"{kind}:{family}" for family in MODEL_SLICES for kind in ("PROXY", "CAPACITY"))


def fit_models(training):
    if not training or any(len(s["y"]) < 100 for s in training):
        raise ValueError("minimum training support per requested session; no substitution")
    dates = [s["summary"]["trade_date"] for s in training]
    if dates != sorted(set(dates)) or any(d >= "2026-10-01" for d in dates):
        raise ValueError("unique chronological development training dates")
    arrays = {k: np.concatenate([s[k] for s in training]) for k in ("base", "capacity", "extras", "y")}
    weights = np.concatenate([np.full(len(s["y"]), 1./len(s["y"])/len(training)) for s in training])
    y = arrays["y"]
    # fit() validates class encoding and the fixed ridge=.01, even for PRIOR.
    history = fit(arrays["base"], y, weights)
    models = {"HISTORY": history}
    for name in MODELS[2:]:
        x = design(arrays["base"], arrays["capacity"], arrays["extras"], name)
        models[name] = fit(x, y, weights)
    return {
        "models": models, "prior": history["prior"].copy(),
        "last_training_date": dates[-1], "training_dates": tuple(dates),
        "feature_counts": {"PRIOR": 0, **{k: len(v["mean"]) for k, v in models.items()}},
        "ridge_lambda": .01, "automatic_selection": False,
    }


def score(data, frozen):
    date = data["summary"]["trade_date"]
    if date <= frozen["last_training_date"] or date >= "2026-10-01":
        raise ValueError("score strictly after fitting and before holdout")
    y = data["y"]
    n = len(y)
    if n == 0:
        raise ValueError("no usable response population; report unavailable, not zero loss")
    loss = {"PRIOR": brier(np.broadcast_to(frozen["prior"], (n, 3)), y)}
    for name in MODELS[1:]:
        x = design(data["base"], data["capacity"], data["extras"], name)
        loss[name] = brier(predict(frozen["models"][name], x), y)
    def group(mask, family=None):
        count = int(mask.sum())
        means = {k: float(v[mask].mean()) if count else None for k, v in loss.items()}
        out = {"anchors": count, "response_counts": np.bincount(y[mask], minlength=3).tolist(),
               "mean_brier": means, "independent_episode_claim": False}
        if family is not None:
            a, c = "PROXY:"+family, "CAPACITY:"+family
            out["paired_delta_proxy_minus_capacity"] = float((loss[a]-loss[c])[mask].mean()) if count else None
            out["paired_delta_proxy_minus_history"] = float((loss[a]-loss["HISTORY"])[mask].mean()) if count else None
        return out
    all_rows = np.ones(n, dtype=bool)
    thin = data["thin_60s"]
    if thin.shape != (n,) or thin.dtype.kind != "b":
        raise ValueError("observed-before-label 60s sensitivity mask")
    result = dict(data["summary"])
    result.update({
        "model_feature_counts": dict(frozen["feature_counts"]),
        "whole_population": group(all_rows), "thin_60s_whole_population": group(thin),
        "primary_transition_subsets": {
            name: {"all_usable": group(data["extras"][:, ix] == 1, name),
                   "thin_60s": group((data["extras"][:, ix] == 1) & thin, name)}
            for name, ix in (("A_TO_E", 4), ("E_TO_A", 5))},
        "ablation_deltas": {
            family: float((loss["PROXY:"+family]-loss["CAPACITY:"+family]).mean())
            for family in MODEL_SLICES},
        "fit_on_evaluation": False, "holdout_opened": False, "raw_exported": False,
        "mechanism_validated": False, "edge_claim": False,
        "history_feature_count": len(HISTORY_NAMES),
    })
    return result