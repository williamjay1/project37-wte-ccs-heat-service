# WtE–CCS thermal-service assessment: reproducible code and data

Research software supporting *Service preserving retrofit boundaries for
carbon capture at waste incineration plants*. This repository
supports a bounded engineering assessment, **not factory validation, a full
multi-impact LCA, bankable TEA or an EU-27 investment forecast**.

## Publication state

Repository: https://github.com/williamjay1/project37-wte-ccs-heat-service .
The preceding snapshot is preserved by tag `v1.0.0` and archived at
https://doi.org/10.5281/zenodo.23180488. It does **not** include the 11 October
service revision. `service_revision_r43/` adds the new numerical construction,
capacity and decision-budget analysis and portable figure production. No new
DOI, GitHub release or author-approved manuscript is asserted for this increment.
A GitHub account name is not inferred to be a paper author. The historical
root `publication_metadata.json` describes the initial preparation and is not
the current archival record; use the resolved Zenodo record for v1 metadata.
Publishing code does not establish journal policy compliance or author approval.
Generative AI assisted research design, source appraisal, code, graphics and
manuscript preparation; exact model provenance was not consistently retained.
Human researchers remain responsible for scientific appraisal and declarations.

## Quick start

The new revision is a separate empty-results run, with its own pinned
dependencies and comparison references:

```shell
cd service_revision_r43
python -m venv .venv
# Activate the virtual environment; do not enable system site packages.
python -m pip install -r requirements.txt
python src/reproduce_revision_with_artwork_r43.py
```

It recomputes thirteen numerical stages, including continuous-domain inner
and independent continuum outer certificates, and checks all 25 scientific
outputs, including independent transport and point-cut checks,
and draws three artwork products; four panel CSVs are checked after plotting.
The script does not upload, archive, mint a DOI or certify visual inspection.
See its README and SOURCE_NOTES for provenance and conditional evidence limits.
The current graphical abstract shows the two-sided thermal service bounds,
not only the older central climate/cost illustration. Its labels are read
from fresh computed outputs. Both original drawing scripts remain available.
The manuscript's immutable `ee987b877fd4de70ec25d37c20cdd075c03177e8`
scientific snapshot is retained; this additive artwork update does not change
the numerical method or imply that a new manuscript was submitted.
The following commands reproduce the **preceding root pipeline**, separately.

Use Python 3.12. Work in an extracted repository or clone, not the raw-data store.
On the originating research computer, calculations and installation caches must
remain on its computational drive. The public runner itself is location-portable.

```shell
python -m venv .venv
# Activate .venv using the appropriate command for your operating system.
python -m pip install -r requirements.txt
python tools/check_repository.py
python reproduce.py --fresh-dir ../project37-run-001
python tools/compare_outputs.py --fresh-dir ../project37-run-001
python -m unittest discover -s tests -v
```

The fresh directory **must not already exist**. No frozen result files are copied
into the calculation. The runner copies source and six computational inputs,
rebuilds processed monthly data, executes 26 scientific stages, then regenerates
the five current figures and audits their PDF text/collisions. It writes results,
logs and cache to that new directory. A nonzero exit means failure; logs identify
the failing stage. No network or restricted data access is required after the
declared Python dependencies are installed. Approximately five minutes is the
previous local scientific runtime, not a universal runtime guarantee.

## What is evidence, what is a scenario?

* `datasets/hagenholz_operator_raw_cc0_20261002.csv` is the actual owner-published
  monthly snapshot: 80 months, January 2020–August 2026, Switzerland (non-EU).
  The six complete years used in seasonal checks are observed **exports**, not
  latent customer demand, hourly factory operations or a CCS intervention.
* The five regional hourly profiles are modeled PLANtoACT timing proxies,
  normalized and scaled by declared heat-service contracts; they are not metered
  district-heating years or a random sample of European plants.
* Residual-feed trajectories interpolate joint modeled UBA endpoints. The year
  coordinate is synthetic, not an observed waste-composition time series.
* Source steam states, recovery quantities and catalogue storage/capture values
  are published anchors. Missing hot composites, turbine off-design states and
  pressure-drop curves are **not** filled in with invented measurements.
* Scenario bands and percentiles are not statistical confidence intervals.
  Optimistic-domain failures exclude service; a pass is only necessary evidence.

See `docs/DATA_SOURCES.json` for each input's URL, version, access date, SHA-256,
  units, license basis, processing and claim limits, and
`docs/DATA_DICTIONARY.json` for actual column names and numeric ranges.
No vendor-confidential appendix, proprietary process software, publisher full
text, copyrighted original figure, font file, token or private correspondence is
included. Third-party libraries are installed separately under their own licenses.

## Reproduction and checking

`.gitattributes` disables automatic line-ending conversion so frozen CSV/JSON
and manifest bytes survive a GitHub clone on Windows and Linux unchanged.

`reference_results/` contains the frozen numeric outputs, not inputs fed back into
the model. `tools/compare_outputs.py` independently compares every numeric field
against a fresh run, excluding only recorded timestamps and solver/wall-clock
diagnostics. It checks identical nonvolatile scenario identities and classifications.
An explicit reference-to-fresh mapping handles the regenerated cleaned CSV used
for Fig. S2. SHA-256 file integrity is **not** scientific validation.

`figures/` contains the five editable SVG/vector PDF masters and native 1200 dpi
PNGs. Vector files have no DPI. Original Arial was not redistributed; a machine
without it can substitute fonts, so pixel-exact equality is not promised across
operating systems. Values, geometry and reproducible checks are the primary
criteria. Inspect new renderings before publication; automated collision checks
cannot replace visual judgment.

The actual 5 October 2026 local source-only run completed all 28 stages in
316.292 seconds. The independent comparison checked 115,348 numeric fields with
zero differences and zero scaled error; see `docs/LOCAL_REPRODUCTION_QC.json`.
This is measured Windows/Python3.12 reproduction, not a claim that Linux or
GitHub Actions has already passed. The CI workflow checks those conditions
separately when run on GitHub.

## Licensing and citation

Original project code is licensed under MIT; its copyright notice does not
identify or certify manuscript authorship. Vendored plotting styles/auditors
retain their MIT/Apache-2.0 notices. Inputs are **not all MIT**: owner CC0,
attributed CC BY 4.0 derivatives, UBA's stated data-use terms and limited published
numerical facts are separated in `DATA_LICENSES.md`. No open license is invented
for a third-party article supplement or report merely because it can be downloaded.

The original upstream PDFs/XLSX files are not redistributed. Use their source
identifiers to access them and retain source notices when reusing the derived
inputs. The frozen source-specific notices take precedence over a repository-wide
default. A software release containing these inputs should describe that mixed
scope explicitly, rather than license the entire archive as MIT.

Run `python tools/prepare_citation.py --metadata publication_metadata.json`
**after filling in real author and repository metadata**. It refuses blank names
and placeholder DOIs. It creates `CITATION.cff` only then. No root `.zenodo.json`
is supplied, avoiding precedence conflicts. Do not create an archival release
until those metadata and human checks are complete. Cite the eventual **version
DOI** associated with the tested release; the concept DOI can identify the series.

## Repository layout

```
src/                 scientific code and licensed graphics helpers
datasets/            six frozen, attributable computational inputs
reference_results/   numerical benchmark outputs; never seeded into a fresh run
figures/             current vector masters and 1200 dpi raster exports
tools/               integrity, comparison and citation-preparation commands
tests/               repository contract tests
docs/                data sources, dictionary, methods and archival guide
```

The manuscript and private submission correspondence are deliberately not part
of the code repository. The paper's complete methods and limitations remain in
the separate main/SI PDF delivery. See `docs/ZENODO_HANDOFF_ZH.md` for the author's
GitHub/Zenodo sequence and `docs/PAPER_AVAILABILITY_STATEMENT.md` for truthful
pre-deposit wording. Do not invent a DOI, ORCID, funding source or author approval.
