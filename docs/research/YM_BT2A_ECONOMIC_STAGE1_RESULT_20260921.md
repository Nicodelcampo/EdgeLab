# YM/BT2A economic campaign — Stage 1 result

## Decision
`STOP_BEFORE_STAGE_2_NO_ECONOMIC_SURVIVOR`

The preregistered discovery screen evaluated 7,128 combinations: 132 entry policies crossed with 54 coarse SL/TP/time-exit/break-even specifications. It processed 8,056,713 discovery ticks and 2,645 BT2A zones strictly before 2026.

No combination was positive after six all-in round-turn ticks. No combination had positive four-tick expectancy after Holm correction. Therefore the 69,120-combination refinement stage was not opened. Continuing solely to search for a winner would be p-hacking, not recursive improvement.

## Best observed combination
- Entry: departure 8 ticks, shallow retest, 100-tick expiry
- Exit: SL 6, TP 24, maximum hold 1,000 ticks, break-even off
- Trades: 518
- Mean gross: +1.618 ticks
- Net at 2 ticks: -0.382
- Net at 4 ticks: -2.382
- Net at 6 ticks: -4.382
- Holm p at four ticks: 1.0

The optimized evaluator was checked with the canonical policy and trade simulators. Trade count and mean matched exactly.

## Defects fixed before accepting the result
1. A retest touch had been used as its own fill. It is now only a trigger; execution is the first later observed tick in the same session or abstention.
2. The optimized exit evaluator crossed session boundaries. It now stops at session end. The initial output was discarded and all 7,128 combinations were rerun.

## Interpretation
The rectangle is frequently revisited, but the tested bounce-management family does not cover conservative friction in discovery. The correct Brain action is to remember the negative result, diagnose a new mechanism or conditioning variable, and preregister a new family—not silently broaden the current grid.

Validation outcomes and H2-2026 remained unopened. Promotion ceiling remains `LESSON_CANDIDATE`.

## Aporte al referente
Demonstrates a functioning fail-closed improvement loop: broad but finite search, causal repair, independent verification, multiplicity control and an explicit stop when evidence does not justify further refinement.
