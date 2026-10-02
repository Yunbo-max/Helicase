# Helicase revision tools v2

[中文运行指南](README_ZH.md) | [Evaluation protocol](EXPERIMENT_PROTOCOL.md) | [Software validation](VALIDATION.md)

Reuse the original SCQA dataset and saved outputs first. This directory does not alter the core Helicase algorithm, the dataset, or historical results. Nothing starts a full rerun automatically.

From the repository root, in your Python 3.10+ environment:

```bash
git pull --ff-only origin main
python -m pip install -r reviewer_analysis/revision_v2/requirements.txt
python -m pytest -q
python -m reviewer_analysis.revision_v2 --help
```

Start offline; replace the archive path with your own file:

```bash
python -m reviewer_analysis.revision_v2 prepare \
  --archive /path/to/results.zip \
  --out reviewer_analysis/revision_v2/private/archive_v2
```

Use a new output directory if one already exists. The supplied archive is read, not overwritten. No API key is needed for this step.

For API-backed evaluation, copy `.env.example` into `private/.env` and set the judge endpoint, model and key there. For native repeats, your complete local `helicase` and `helix_core` source packages and search credentials are also required. Do not commit secrets or raw data.

The native runner is serial. `--max-jobs` is a launch-count cap, not concurrency. Paid commands require `--execute`. Only `full` and `search_n1` are connected native variants; the strict four-method matched-budget comparison is a protocol, not a completed runner. Tests use synthetic fixtures and mocked API responses, not paid live experiments.
