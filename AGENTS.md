# Repository Guide

This is a Marivo-first analytical project over the December 2025 NYC TLC Yellow Taxi file.

- Run `make setup` before analysis. It installs Marivo and verifies the semantic
  layer against the remote CloudFront trip Parquet and Taxi Zone lookup CSV.
- Never use bare `python`, `pip`, `pytest`, `mypy`, or `ruff`. Use the Make
  targets or `.venv/bin/...`.
- Start analysis from the governed objects under `models/`; do not replace
  semantic metrics with ad-hoc SQL.
- Use `import marivo.semantic as ms` for exact refs and
  `import marivo.analysis as mv` for analysis.
- Inspect Frame results progressively: use `repr(frame)` and `frame.show()` for
  captured facts; `show()` also provides a bounded preview when fixed. Inspect
  `frame.schema` and `frame.lineage` for structure and origins; for fixed results,
  read `frame.source_reads` and `frame.method_facts` when needed.
- For a pending Frame, call `compute()` or `persist()` and continue with the
  returned Frame before reading data. Use `read_page()` for bounded rows and
  `read_periods(axis)` for saved time periods; use `to_pandas()` when a complete
  export is needed.
- Treat TLC timestamps as local `America/New_York` wall-clock timestamps.
- Treat policy and weather explanations as observational. Marivo does not make
  causal claims from before/after comparisons or correlations.
- Raw SQL is a diagnostic escape hatch only. If used, reconcile the result to
  the semantic metric before reporting it.
- Keep the published records intact during analysis and disclose any scope or
  data-quality filters used.
- Put local analysis scripts under `analysis/` and keep generated session state
  under `.marivo/` out of Git.
