# mishna_new

Sends a daily Mishna with commentary to a WhatsApp group (via Whapi) and a Telegram channel (`@mishna`). Runs as a Cloud Run Job on GCP, scheduled twice a day on weekdays in Israel.

> ⚠️ **The deployed code lives on the `gcp` branch, not `master`.** Master is essentially stale/legacy. Pushes to master do nothing in production. Always work on `gcp` (or merge into it) — see the [CI/CD](#cicd) section.

## What the code does

Every run advances one Mishna in sequence:

1. Read the current position (`masechet`, `chapter`, `mishna`) from GCS.
2. Check if today (or tomorrow, for the noon run) is a Jewish holiday — if so, skip and return early without advancing the pointer.
3. Fetch the Mishna text from Sefaria.
4. Scrape commentary glosses (`<small>` tags) from Hebrew Wikisource's "ביאור" pages.
5. Build a formatted message: title, bolded Mishna text, italicized inline glosses, commentary links (Bartenura/Rambam/Wikisource), and any extra explanation tables.
6. Send the message to Whapi + Telegram.
7. Query Wikisource for the next Mishna's metadata, write the new position back to GCS.

### Files (`gcp` branch — the deployed code)

| File | Role |
| ---- | ---- |
| `main.py` | Container entry point. Holiday-gating + dispatches to `get_mishna.main()`. |
| `get_mishna.py` | Scraping, formatting, and send logic. |
| `is_yomtov.py` | `is_holiday(date)` — calls Hebcal for Jerusalem and returns whether the given date is a yom tov (and optionally Tisha B'Av). |
| `persistance.py` | GCS read/write helpers (`get_blob_as_dict`, `save_dict_as_blob`). |
| `Dockerfile` | uv-based, Python 3.12 alpine. |
| `.github/workflows/deploy.yml` | GH Action that builds + pushes the image on each `gcp` push. |

### Files (`master` branch — legacy / scratch)

| File | Role |
| ---- | ---- |
| `get_mishna.py` | Older variant of the same scraper. Standalone-script-style (`open(argv[1])`, no GCS). Not deployed. |
| `get_next.py` | Standalone helper to compute the next-Mishna pointer. Duplicate of logic in `get_mishna.py`. |
| `is_yomtov.py`, `is_erev_yomtov.py` | Old script-style holiday checks (top-level `exit(1)`). Replaced by `is_yomtov.py:is_holiday()` on `gcp`. |
| `current.json` | Sample/legacy state file. **Not the source of truth** — actual state is in GCS. |
| `mishna`, `mishna_afternoon` | Compiled python 3.6 binaries, legacy. |
| `do_mishna`, `do_mishna_afternoon`, `upload_current` | Old shell wrappers, legacy. |
| `run.sh` | Local invocation via pipenv (outdated, still references pipenv). |
| `dry_run.sh`, `.dry_run.json` | Local dry-run. **`.dry_run.json` contains live secrets — see [Security](#security).** |
| `Pipfile`, `Pipfile.lock`, `requirements.txt` | Legacy dependency files; superseded by `pyproject.toml` + `uv.lock`. |
| `pyproject.toml`, `uv.lock` | Current dependency definition (uv-managed, Python ≥ 3.12). Mirrored on both branches. |

### Key functions in `get_mishna.py` (gcp branch)

- `deserialize(config)` / `serialize(config, …)` — read/write the position JSON from GCS via `persistance.py`.
- `get_mishna_text(…)` — Sefaria API for the Mishna text.
- `get_commentary(…)` — scrapes `<small>` tags from Wikisource's `ביאור:משנה_<masechet>_פרק_<chapter>` page for inline glosses.
- `get_commentary_url(…)` — generates URLs (Bartenura, Rambam, Wikisource) without fetching content.
- `get_next_mishna(…)` — fetches the Mishna page's wikitext template and parses the `next` field.
- `get_unvariated_masechet` / `get_variated_masechet` — normalize spelling variants of tractate names between Wikisource pages and Sefaria refs.

Note: two functions are both named `get_mishna_part` (lines 89 and 127). The second shadows the first. The first is dead code.

## Deployment

### Where it runs

- **GCP project:** `personal-assistant-454804`
- **Cloud Run Job:** `mishna-morning` in `europe-west1` (despite the name, this single job is used for both morning and afternoon runs)
- **Image:** `europe-west1-docker.pkg.dev/personal-assistant-454804/mishna/mishnaimage` (Artifact Registry)
- **Runtime service account:** `mishna-bot-sa@personal-assistant-454804.iam.gserviceaccount.com`
- **Resources:** 512Mi memory, 1 vCPU, 10m task timeout, max 3 retries.

### Schedule

Two Cloud Scheduler jobs (in `europe-west1`, both `timeZone: Asia/Jerusalem`), both POSTing to `mishna-morning:run` via the `mishna-launcher@…` service account:

| Scheduler job | Cron (Israel time) | Days | Israel local time | Notes |
| ------------- | ------------------ | ---- | ----------------- | ----- |
| `mishna-morning-trigger`   | `0 7 * * 0-5`  | Sun–Fri | 07:00 | Skips Shabbat (Sat). |
| `mishna-afternoon-trigger` | `0 14 * * 0-4` | Sun–Thu | 14:00 | Skips Friday (erev Shabbat) and Shabbat. |

The Cloud Run execution timestamps shown in `gcloud run jobs executions list` are UTC, so for example "11:00 UTC" in summer = 14:00 Israel (DST). The cron itself is set in Israel local time and adjusts for DST automatically.

### Friday / Shabbat / Yom Tov logic

This is split between **schedule-level gating** (when not to fire at all) and **runtime gating** (when not to send even if fired):

- **Shabbat gating:** baked into the cron — the morning trigger runs Sun–Fri (`0-5`), so it never fires on Saturday. The afternoon trigger runs Sun–Thu (`0-4`), so it never fires on Friday or Saturday.
- **Friday afternoon gating:** baked into the afternoon cron (`0-4`) — no afternoon run on Friday, because by 14:00 Israel time it's already erev Shabbat in spirit (and to avoid sending after candle-lighting on short winter Fridays).
- **Yom Tov gating (runtime):** `main.py` calls `is_holiday(today)`; if true, it returns `{"message": "Today is a holiday!"}` and never invokes `get_mishna_main()`. The position pointer is NOT advanced — same Mishna will go out the next non-holiday day.
- **Erev Yom Tov gating (runtime, dormant):** `main.py` has a `noon` parameter; when `noon=True`, it also checks `is_holiday(tomorrow)`. But the container's `CMD` invokes `get_mishna()` with no args, so `noon` defaults to `False` and this check **never runs in production**. The afternoon trigger gets the morning behavior — only today's holiday is checked, not tomorrow's.
- **Tisha B'Av:** treated as a holiday by `is_holiday` (the parameter `tisha_beav_as_holiday=True` defaults true).

`is_holiday(date)` queries `hebcal.com/hebcal?...&city=IL-Jerusalem&i=on` (Israel observance) for the date's month and returns true if any item for that date has `yomtov: true`. It also sends a debug message to a hardcoded Telegram chat id (215513269) describing the day.

### Environment

| Var | Value |
| --- | ----- |
| `GOOGLE_STORAGE_BUCKET` | `mishna` |
| `SERIALZIZATION_FILENAME` | `current.json` *(misspelling preserved in code)* |
| `TELEGRAM_GROUP` | `@mishna` |

### Secrets (Secret Manager)

| Container env var | Secret name |
| ----------------- | ----------- |
| `MISHNA_GROUP` | `MISHNA_GROUP` |
| `TELEGRAM_TOKEN` | `telegtam-token` *(typo preserved)* |
| `WHAPI_AUTH` | `whapi-token` |

### Dockerfile (`gcp` branch)

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-alpine
COPY uv.lock pyproject.toml /app/
WORKDIR /app
RUN uv sync --frozen --no-install-project
COPY *.py .
CMD ["uv", "run", "python", "main.py"]
```

## CI/CD

- **GitHub repo:** `abloch/mishna_new`
- **Workflow:** `.github/workflows/deploy.yml`, present **only on the `gcp` branch**.
- **Trigger:** push to `gcp` branch only. **Pushes to `master` do nothing.**
- **What it does:** authenticates to GCP via the `GCLOUD_SERVICE_ACCOUNT` GitHub secret, builds the Docker image, pushes it to Artifact Registry with `:${{ github.sha }}` and `:latest` tags (with retry logic).
- **What it does NOT do:** does **not** update the Cloud Run Job spec. The job's spec is pinned to a specific image `@sha256:…`. Pushing a new `:latest` doesn't redeploy the running job. Updating the job to use the new image requires a manual `gcloud run jobs update mishna-morning --region=europe-west1 --image=…:latest` (or by sha).
- **Image-push service account:** `gh-action-image-pusher@personal-assistant-454804.iam.gserviceaccount.com`
- Unused workflow env: `JOB_NAME: my-job` is set but never referenced — leftover scaffolding.

### To deploy a fix

1. Apply the change on the `gcp` branch (cherry-pick or push directly).
2. Wait for the workflow to build and push the new image.
3. Manually point the Cloud Run Job at the new image (sha or `:latest`).

## Storage

- **GCS bucket:** `mishna`
- **Object:** `current.json` — **source of truth** for the current position. Schema: `{"masechet": "<hebrew name>", "chapter": "<hebrew letter>", "mishna": "<hebrew letter>"}`. Numbers are written as Hebrew gematria letters (e.g. `"ה"` for 5, `"ט"` for 9).
- Read at the start of each run via `persistance.get_blob_as_dict`, written back via `save_dict_as_blob` after a successful send.

## Sources

- **Hebrew Wikisource** (`he.wikisource.org`) — Mishna commentary pages (`ביאור:משנה_<masechet>_פרק_<chapter>`) and Mishna metadata (for next-pointer logic).
- **Sefaria** (`sefaria.org.il`) — Mishna text and reference URLs for Bartenura, Rambam, Tosafot Yom Tov.
- **Hebcal** (`hebcal.com`) — Jewish-calendar holiday data (Israel/Jerusalem observance).

## Local / dry-run

Local dry-run (from `master`):
```bash
./dry_run.sh
# or
uv run python get_mishna.py .dry_run.json
```

`.dry_run.json` sets `DRY_RUN: true`. In `send_to_telegram`, when `DRY_RUN` is set, messages are routed to Telegram chat id `215513269` instead of `@mishna`. Whatsapp sending is gated by `LOCAL` in `send_all`.

There is no automated test suite.

## Other Cloud Run Jobs in the same project (unrelated)

`fbscrape`, `health-checker-job`, `whapi-health-checker`, `yeshanot`.

## Security

- `.dry_run.json` is committed to git and **contains a real Telegram bot token and a Whatsmate client secret**. These should be rotated and the file moved out of version control.
