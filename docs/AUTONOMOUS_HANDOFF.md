# Resume the Beed drought study with authenticated network access

User authorization: Abhay explicitly authorized implementing the plan, obtaining the
needed data, executing analyses, inspecting results and fixing errors autonomously.
Do not ask again for routine implementation or execution permission. Do not send
messages to others or publish results. No new ML architecture is authorized as a
scientific conclusion; choose a model only after data and target validity support it.

Workspace: `/Users/abhay/Desktop/gnr605`. Existing git-backed project; preserve user
changes and all older scripts. Do not duplicate the project into ChatGPT Library.

## Access needed

The previous session had no ee package, no Earth Engine or Google ADC credentials,
no browser-control tools, and DNS/network failures for public data and Google APIs.
A new chat with identical restrictions will not solve this. Use a local Codex session
with terminal/network access and access to this same workspace.

The user must complete their own Google login, using an Earth Engine enabled Cloud
project from their existing Code Editor. Do not request passwords, API tokens, service
account private keys or credential-file uploads. Credentials should remain local.
Setup in the user's normal terminal (replace YOUR_PROJECT_ID before running):

```sh
cd /Users/abhay/Desktop/gnr605
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r pipeline/study/requirements.txt
python -c "import ee; ee.Authenticate(); ee.Initialize(project='YOUR_PROJECT_ID'); print(ee.Number(1).getInfo())"
python pipeline/study/check_access.py --project YOUR_PROJECT_ID
```

Successful `ee.Number(1).getInfo()` should print 1. That verifies package, credentials,
project and API access. It does not prove every dataset/export permission works.
The agent runtime must also reach Google APIs; login on the host does not remove a
separate runtime network restriction. Do not expose credential contents in tool output.

## Current implementation and actual results

- `pipeline/study/export_study_gee.js`: complete GEE script preparing three exports,
  four controlled variants, Oct–Dec 2020–2024, rebuilt 2001–2019 references,
  own/shared-support metrics and 1981–2024 monthly CHIRPS. JS syntax checked ONLY.
- `pipeline/study/analysis.py`: real-export validator, monthly SPI-1/3/6/12 with
  training-only fits, exploratory rainfall trend estimates, and actual-data coverage
  bounds. Seven tests passed, including leakage, missing months, zero mass and
  random spatial-set checks for the bounds.
- `results/study/execution_status.json`: new satellite and SPI results explicitly
  awaiting exports. No new satellite data has been downloaded or computed locally.
- `results/study/screened_coverage_bounds.csv`: ACTUAL derived bounds from the full
  real detailed-QA export. October screened NDVI coverage lies within 85.15–86.57%
  in 2021; exactly 84.77% in 2023; 63.97–82.44% in 2024. These are mathematical
  set bounds, not confidence intervals or final VHI footprints.

The earlier 174-row detailed QA export covers all 54 expected composites; internal
checks and four corruption-detection tests passed. Review `results/andure/` rather
than repeating that investigation. Raw-reader extracts retain upload identities.
Usefulness code 3 is observed but omitted in the catalogue's label list; do not guess
its semantics. The screened candidate excludes it and all high-aerosol marginal data.

## Next actions, in order

1. Verify network/authentication with `check_access.py`. Once available, implement a
   Python EE executor matching the JS experiment or use a legitimately available
   browser runner. The Python executor has NOT yet been implemented. Use official
   credentials; never scrape browser tokens. Submit the jobs and obtain their outputs
   autonomously where the available APIs permit it, with bounded retries/checkpoints.
2. Execute the three exports. Expected filenames/rows are documented in
   `pipeline/study/README.md`: 120 comparison, 288 history, 528 rainfall rows.
   Download to `data/study/` and run `analysis.py`. Do not invent results if blocked.
3. Inspect server errors and correct them. Local syntax alone is not an EE test.
   Check A/October/2020 against existing strict preview: coverage 0.2617443143005018,
   VHI 91.427477222441, district MODIS-grid area 11412.55645769558 km².
4. Verify monthly NDVI history against already audited October values. Screened
   current coverage must lie inside the derived bounds. C includes strict observations
   but VCI/VHI eligibility is not necessarily nested due to altered reference spans.
5. Inspect own/shared-support class changes, out-of-range indices, baseline spans
   and LST daily observation counts. D–C changes LST product/aggregation, so do not
   call it a pure date-mask effect. Unknown pixels remain unclassified.
6. Inspect SPI fit diagnostics and old October rainfall consistency; produce actual
   plots and a research results note. Do not infer crop damage from SPI alone.
7. Verify AOI against authoritative Beed geometry, acquire crop/irrigation masks and
   crop-yield data if accessible. Report gaps. Only then evaluate independent impact
   agreement or expand to other districts. No automatic novelty or forecasting claim.

## Scientific guardrails

Our plan uses Somni's seasonal-index framework and Taji/Keskar's precipitation/SPI
framework as methodological baselines. The original Andure ML predictor set contains
VCI and TCI while VHI is their weighted combination; high predictive fit is not evidence
of early warning. Somni does not implement SPI validation in the full paper, despite
an incorrect statement in old meeting notes. Kulkarni et al. 2020 already combines
SPI/NDVI/LST/soil moisture and yield comparison for Marathwada, so combinations alone
are not novel. Read `literature/notes/paper_review.md` for exact limitations.

Do not fit trend claims or neural networks to five October means. A temporal model
would require a prospective target, sufficient independent seasons, correct data
availability cutoffs, held-out years, and persistence/seasonal/simple-model baselines.

Suggested opening prompt for the new session:

> Read docs/AUTONOMOUS_HANDOFF.md and pipeline/study/README.md. I authorize you to
> continue the Beed study autonomously. Verify authenticated Earth Engine access,
> execute the controlled comparison and rainfall pipeline, retrieve outputs, test
> and fix failures, and produce actual results. Do not repeat completed QA work or
> treat unexecuted code as results. Only stop for a login or permission I must perform.
