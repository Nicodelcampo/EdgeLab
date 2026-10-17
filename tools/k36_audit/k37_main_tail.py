
# ======================================================================================
# K37 (pre-registrado: docs/research/K37_PREREGISTRO_CORREDOR_X_HFT_LADDER_TRAP_20261017.md)
# Una unica variante, sin ranking ni ML. Ventana de REPLICACION abr-sep 2026 (< 20261001).
# ======================================================================================
K37_START, K37_END = 20260401, 20260930
K37_COST = 1.546
K37_NULL_REPS = 2000
K37_MIN_SESSIONS = 80


def _k37_nonoverlap_select(df):
    """Misma regla causal de k36: una posicion a la vez, por sesion, en orden de cierre del impulso."""
    sids = df["session_id"].values
    cls_bars = df["cls_bar"].values
    res_bars = df["bars_res_sym"].values
    keep = np.zeros(len(df), dtype=bool)
    last_sid, active_exit = -1, -1
    for i in range(len(df)):
        s_i, cb_i = int(sids[i]), int(cls_bars[i])
        if s_i != last_sid:
            last_sid, active_exit = s_i, -1
        if cb_i <= active_exit:
            continue
        keep[i] = True
        active_exit = cb_i + max(int(res_bars[i]), 1)
    return keep


def _k37_cluster_mean(x, sid):
    """Media y SE clusterizado por sesion (varianza de totales por sesion, Liang-Zeger)."""
    n = len(x)
    if n < 2:
        return float("nan"), float("nan"), 0
    mu = float(np.mean(x))
    d = pd.DataFrame({"s": sid, "r": x - mu}).groupby("s")["r"].sum().values
    g = len(d)
    if g < 2:
        return mu, float("nan"), g
    se = math.sqrt((g / (g - 1.0)) * float(np.sum(d ** 2))) / n
    return mu, se, g


def _k37_arm_metrics(df_arm):
    sel = _k37_nonoverlap_select(df_arm)
    d = df_arm[sel]
    gross = d["gross_2s_sym"].values.astype(float)
    sid = d["session_id"].values
    filled = d["pas_filled_sym"].values == 1
    pas_net = d["pas_gross_2s_sym"].values.astype(float)[filled] - K37_COST
    out = {"n_trades": int(len(d)), "n_passive_filled": int(filled.sum()),
           "n_sessions_with_trades": int(len(np.unique(sid))),
           "trades_per_day": float(len(d) / max(len(np.unique(df_arm["session_id"].values)), 1))}
    for name, x, s in (("gross_0t", gross, sid),
                       ("net_limit_155t_immediate", gross - K37_COST, sid),
                       ("net_passive_tt_state_machine_155t", pas_net, sid[filled])):
        mu, se, g = _k37_cluster_mean(x, s)
        out[name] = {"mean_ticks": mu, "se_clust": se, "n": int(len(x)), "n_clusters": int(g),
                     "lower_975": mu - 1.96 * se if se == se else float("nan"),
                     "upper_975": mu + 1.96 * se if se == se else float("nan"),
                     "z_clust": (mu / se) if (se == se and se > 0) else float("nan")}
    return out, d


def main_k37():
    t0 = time.time()
    pfile = locate_es_parquet()
    sessions_list, cmap, has_vol = dev_load_sessions(pfile)
    sessions_list = [s for s in sessions_list if K37_START <= s["trade_date"] <= K37_END]
    tds = sorted(set(int(s["trade_date"]) for s in sessions_list))
    print("K37: sesiones en ventana de replicacion:", len(sessions_list),
          "rango", (tds[0], tds[-1]) if tds else None, flush=True)
    assert tds and tds[-1] < 20261001, "HOLDOUT: hay sesiones >= 2026-10-01"
    if len(sessions_list) < K37_MIN_SESSIONS:
        print("K37_ABORT_DATA_INSUFFICIENT sesiones=%d < %d (no se miden retornos)" % (len(sessions_list), K37_MIN_SESSIONS), flush=True)
        return

    out_dir = Path(os.environ.get("STUDY_OUT", "/kaggle/working"))
    out_dir.mkdir(parents=True, exist_ok=True)
    # incluye la prueba causal y la de prefijo HFT v2 (no vacua): si falla, aborta antes de medir retornos
    df_p1, df_p2, seqs_p1, seqs_p2, causal_tests, n_hft_total = run_k36_trajectory_extraction(sessions_list, out_dir)

    u1 = df_p1[df_p1["has_hft_w1"] == 1].sort_values(["session_id", "cls_bar"]).reset_index(drop=True)
    n_sessions_u1 = int(u1["session_id"].nunique())
    arms = {"ARM_ALL": u1, "ARM_NOLADDER": u1[u1["opp_ladder_trap_flag"] == 0].reset_index(drop=True),
            "ARM_LADDER_ONLY": u1[u1["opp_ladder_trap_flag"] == 1].reset_index(drop=True)}
    res_arms, selected = {}, {}
    for k, v in arms.items():
        res_arms[k], selected[k] = _k37_arm_metrics(v)
        print("K37", k, json.dumps({a: (b["mean_ticks"] if isinstance(b, dict) and "mean_ticks" in b else b)
                                      for a, b in res_arms[k].items()}), flush=True)

    # Nulo (para H1): exclusion ALEATORIA del mismo numero de impulsos (sin mirar el flag).
    obs = res_arms["ARM_NOLADDER"]["net_passive_tt_state_machine_155t"]["mean_ticks"]
    n_excl = int((u1["opp_ladder_trap_flag"] == 1).sum())
    rng = np.random.default_rng(20261017)
    null_means = []
    for _ in range(K37_NULL_REPS):
        drop = rng.choice(len(u1), size=n_excl, replace=False)
        mask = np.ones(len(u1), dtype=bool)
        mask[drop] = False
        m, _d = _k37_arm_metrics(u1[mask].reset_index(drop=True))
        null_means.append(m["net_passive_tt_state_machine_155t"]["mean_ticks"])
    null_means = np.asarray(null_means, dtype=float)
    p_null = float((1 + np.sum(null_means >= obs)) / (K37_NULL_REPS + 1.0))

    prim = res_arms["ARM_NOLADDER"]["net_passive_tt_state_machine_155t"]
    verdict = "ABSTENCION"
    if prim["lower_975"] > 0 and p_null <= 0.025:
        verdict = "SOPORTADA"
    elif prim["upper_975"] < 0.5:
        verdict = "NO_SOPORTADA"

    # descriptivo por mes
    u1m = u1.copy()
    u1m["month"] = (u1m["session_id"].map({int(s["session_id"]): int(s["trade_date"]) // 100 for s in sessions_list})).values
    by_month = {}
    for mth, g in u1m[u1m["opp_ladder_trap_flag"] == 0].groupby("month"):
        mm, _d = _k37_arm_metrics(g.reset_index(drop=True))
        by_month[str(mth)] = {"n_trades": mm["n_trades"], "net_pas_mean": mm["net_passive_tt_state_machine_155t"]["mean_ticks"]}

    summary = {
        "spec_id": "EXP-K37-CORREDOR-HFT-LADDER-TRAP-REPLICATION-V1", "manifest": "K37_PREREGISTRO_CORREDOR_X_HFT_LADDER_TRAP_20261017.md",
        "window": [K37_START, K37_END], "n_sessions_window": len(sessions_list), "n_sessions_u1": n_sessions_u1,
        "n_impulses_u1": int(len(u1)), "n_ladder_trap": n_excl, "holdout_touched": False,
        "causal_tests": causal_tests, "arms": res_arms,
        "null_random_exclusion": {"reps": K37_NULL_REPS, "observed_net_pas": obs, "null_mean": float(np.mean(null_means)),
                                  "null_p975": float(np.quantile(null_means, 0.975)), "p_value": p_null},
        "by_month_noladder_net_pas": by_month, "VERDICT_PRIMARY": verdict, "elapsed_seconds": round(time.time() - t0, 1),
    }
    print("=== EXP_K37_SUMMARY_START ===", flush=True)
    print(json.dumps(summary, indent=2, default=float), flush=True)
    print("=== EXP_K37_SUMMARY_END ===", flush=True)
    (out_dir / "EXP_K37_RESULTS_20261017.json").write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")


main_k37()
