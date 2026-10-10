# Service-preserving retrofit revision (11 October 2026)

This version adds nine numerical stages, a continuous-domain thermal certificate
and three portable artwork products to
the preceding pipeline at the repository root. It is not a new plant dataset,
a full multi-impact LCA, a complete joint steam-cycle validation, a bankable
TEA, a journal acceptance, or a new Zenodo deposit. The preceding v1.0.0 DOI
does not cover this revision. Historical r41/r42 script/figure stems are
computational identifiers, not current manuscript figure numbers.

## Run from empty numerical outputs

Use Python 3.12 in a virtual environment without system site packages:

    python -m pip install -r requirements.txt
    python src/reproduce_revision_with_artwork_r43.py

Run from this directory, which must initially have no results. On the
originating Windows computer use D: for calculation; non-Windows paths are
portable. The runner recomputes before comparing all 21 numerical products
with reference/outputs. Reference values are not scientific calculation
inputs. Four artwork panel CSV payloads are compared byte-for-byte after plotting,
normalizing CRLF/LF line endings only. Numeric, label and other whitespace
differences still fail; the raw-byte comparison is also recorded.
No source PDF, paid database, skill installation, raw drive or account is
needed. Logs and new numerical outputs remain untracked.

For artwork only after a completed run, append --artwork-only. That mode does
not claim a new numerical reproduction. Actual vector/PDF visual inspection
is a separate step, not self-certified by a successful runner.

## Evidence and boundaries

SOURCE_NOTES.md distinguishes published UK and Swiss process anchors from
declared service, missing-state and uncertainty scenarios. Reference outputs
are deterministic model products, not empirical sampling observations.
Retain method-failed paths, negative budgets and endpoint derating failures.
Grid fractions are not confidence intervals or estimated probabilities.
The continuous-domain certificate proves source-curve dominance within the
declared rectangular domain and uses one common conservative temperature
grid. It permits adaptive allocations, not one installed exchanger network.
The 512 interior checks are falsification diagnostics, not the coverage proof.
An independent 64-case transportation LP checks finite-cut sufficiency; all
12 lower/upper capacity brackets are separately checked without the allocator.
Useful-heat derating retains nominal heat-pump electricity and rejects unused
nominal hot output; it is not a fitted part-load COP or an electricity saving.
These common-grid capacities are distinct from endpoint-specific subdivision
results; both numerical products remain available without relabeling them.
The 95 percent family is proportionally calibrated, not a reproduced pilot.
The positive finite path is conditional on the declared temperature/duty
curves; it does not certify installed hardware, annually firm heat or one
common heat-exchanger network across all endpoints. Generic catalogue
capital is a capacity-proportional stress, not a marginal upgrade quotation.

Original project software follows the scoped root LICENSE. Third-party
numerical facts and SciencePlots styles retain the root DATA_LICENSES.md and
THIRD_PARTY_NOTICES.md notices. No full source publication, raw acquisition
file, private plant data, author declarations or unpublished paper is bundled.
