# Service-preserving retrofit revision (11 October 2026)

This version adds thirteen numerical stages, continuous-domain inner/outer certificates
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

For the current r47 full-method and origin-accounting revision, use instead:

    python -m unittest discover -s tests -v
    python src/reproduce_fulltext_revision_r47_20261011.py

This wrapper recomputes all preceding service stages and artwork, then adds
one deterministic printed-source/origin stage. All 30 scientific products
(25 thermal and five new diagnostic files) are compared only after calculation.
The additional JSON reference's timestamp and timestamped ledger digest are
excluded explicitly; all scientific quantities, schemas and labels are checked.
No original source PDF or private factory series is needed. See R47_NOTES.md
for the actual nearest-neighbor overlap and origin-accounting claim boundary.
The preceding runner remains available for the unchanged thermal increment.

Run from this directory, which must initially have no results. On the
originating Windows computer use D: for calculation; non-Windows paths are
portable. The runner recomputes before comparing all 25 numerical products
with reference/outputs. Reference values are not scientific calculation
inputs. Four artwork panel CSVs are compared after plotting with exact schema,
labels and row structure, and a 1e-12 scaled numerical tolerance (tighter than
the 1e-10 scientific-output tolerance). Raw and CRLF/LF-normalized byte identity
are recorded separately. Number/label/space mutations beyond this explicitly
declared floating-point tolerance fail; reference values are not overwritten.
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
The r46 continuum point cuts additionally provide necessary physical upper
bounds within the fixed HP route: the 77 C witness excludes the worst-profile
99.72 percent36.5 MW contract independently of interval matching. The finite
grid failure upper remains separate. At0.05 K, common-service inner/outer
bounds are35.9794/35.9976 MW and36.8119/36.8221 MW for the nominal99.72 and
calibrated95 percent families. These are certificate gaps, not confidence
intervals or verified factory ratings. The latter's uniform thermal derating
limit is bracketed at0.847--0.875 percent with nominal HP power retained.
See CONTINUUM_OUTER_CUTS_R46.md for the derivation and witness scope.
The current graphical abstract, drawn by
`src/draw_service_certificate_GA_r46_20261011.py`, reads the 0.05 K nominal
construction/continuum capacity brackets and the fixed-service audit from
fresh results. At the target's 80 x 30 mm size it displays sufficient inner
and necessary outer bounds, not confidence intervals or measured ratings.
The calibrated 95 percent qualification and worst-profile exclusion at
99.72 percent are retained. Approximate displayed values are rounded; all
decisions use unrounded values. Output includes editable SVG, embedded-font
vector PDF/EPS and native 1200 dpi PNG. Bounding-box checks are separate from
actual visual inspection. The old central climate/budget diagram script is
retained as a historical illustration, not the current graphical abstract.
The positive finite path is conditional on the declared temperature/duty
curves; it does not certify installed hardware, annually firm heat or one
common heat-exchanger network across all endpoints. Generic catalogue
capital is a capacity-proportional stress, not a marginal upgrade quotation.

Original project software follows the scoped root LICENSE. Third-party
numerical facts and SciencePlots styles retain the root DATA_LICENSES.md and
THIRD_PARTY_NOTICES.md notices. No full source publication, raw acquisition
file, private plant data, author declarations or unpublished paper is bundled.
