# Baseline before optimization

[CI run](https://github.com/8554859-cell/findex/actions/runs/45475052468) — 11,284 passages; cProfile index 3.104 s, search 0.715 s. py-spy recorded both flamegraphs (artifact lab08-baseline-profile). Scalene command failed because its CLI changed.

Hypotheses recorded before vectorization:
- store.load: 0.660 s cumulative, including JSON decoding (0.145 s); avoid per-request loading as in Lab 7.
- build_partial: 1.306 s cumulative, 0.328 s self; Python postings/counting overhead.
- tokenize: 0.372 s cumulative, 0.271 s self; Python generator and regex boundary overhead.
These are cProfile timings, not a measured native/Python split. Vectorize the ranking loop, keep the baseline for parity and comparison.
