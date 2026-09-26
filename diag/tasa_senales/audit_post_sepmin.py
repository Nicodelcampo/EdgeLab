"""Audita si post_sepmin.json alcanza para cerrar EXPLORE-001 §1.

No mira outcomes. Verifica cobertura de sesiones, contratos, indicadores y
coherencia de conteos. Un piloto parcial nunca se convierte en censo por tener
medias plausibles.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


class CensusAuditError(ValueError):
    pass


def audit(payload, *, expected_days=200):
    if not isinstance(expected_days, int) or isinstance(expected_days, bool) or expected_days < 1:
        raise CensusAuditError("expected_days debe ser entero positivo")
    if not isinstance(payload, dict) or not payload:
        raise CensusAuditError("payload debe contener contratos")
    all_dates, indicator_sets, totals = set(), [], {}
    problems = []
    for contract, block in payload.items():
        if not isinstance(contract, str) or not isinstance(block, dict):
            raise CensusAuditError("contrato mal formado")
        dates = block.get("fechas")
        indicators = block.get("ind")
        if not isinstance(dates, list) or not dates or len(set(dates)) != len(dates):
            raise CensusAuditError("%s: fechas ausentes o duplicadas" % contract)
        duplicate_cross = all_dates.intersection(dates)
        if duplicate_cross:
            raise CensusAuditError("sesiones repetidas entre contratos: %s" % sorted(duplicate_cross))
        all_dates.update(dates)
        if not isinstance(indicators, dict) or not indicators:
            raise CensusAuditError("%s: indicadores ausentes" % contract)
        indicator_sets.append(set(indicators))
        for name, result in indicators.items():
            if not isinstance(result, dict) or "error" in result:
                problems.append("%s/%s: error o resultado ausente" % (contract, name))
                continue
            if result.get("n_dias") != len(dates):
                problems.append("%s/%s: n_dias inconsistente" % (contract, name))
            post = result.get("post_por_dia")
            if not isinstance(post, dict) or not set(post).issubset(set(dates)):
                problems.append("%s/%s: post_por_dia inválido" % (contract, name))
                continue
            counts = [post.get(day, 0) for day in dates]
            if any(not isinstance(x, int) or isinstance(x, bool) or x < 0 for x in counts):
                problems.append("%s/%s: conteos inválidos" % (contract, name))
                continue
            slot = totals.setdefault(name, {"signals": 0, "days": 0, "zero_days": 0})
            slot["signals"] += sum(counts)
            slot["days"] += len(dates)
            slot["zero_days"] += sum(x == 0 for x in counts)
    if any(s != indicator_sets[0] for s in indicator_sets[1:]):
        problems.append("familia de indicadores inconsistente entre contratos")
    summaries = {}
    for name, values in sorted(totals.items()):
        summaries[name] = dict(
            signals=values["signals"], days=values["days"],
            mean_per_day=values["signals"] / values["days"],
            zero_days=values["zero_days"])
    n_days = len(all_dates)
    if n_days < expected_days:
        problems.append("cobertura insuficiente: %d/%d sesiones" % (n_days, expected_days))
    return dict(
        status="COMPLETE" if not problems else "INSUFFICIENT",
        expected_days=expected_days, observed_unique_days=n_days,
        contracts=sorted(payload), indicators=summaries, problems=problems)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--expected-days", type=int, default=200)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    raw = Path(args.input).read_bytes()
    report = audit(json.loads(raw), expected_days=args.expected_days)
    report["input_sha256"] = hashlib.sha256(raw).hexdigest()
    text = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
