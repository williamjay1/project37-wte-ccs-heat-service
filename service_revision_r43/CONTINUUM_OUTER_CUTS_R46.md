# Continuous-temperature outer witnesses — revision r46

This strengthens evidence, not a claim to invent pinch analysis or thermal
integration. Sources and missing-state assumptions remain in SOURCE_NOTES.md.
No new observed factory state, joint cycle validation, annual reliability,
economic quote, full LCA or DOI is implied.

## Fixed-route necessary cut

Primary100/60C, customer80/50C, retained HP carrier60->77C:

    A(theta) = [h(100)-h(theta)]/[h(100)-h(60)]
    B(theta) = max([h(77)-h(theta)]/[h(77)-h(60)],0)
    D*A(theta) - Qhp*B(theta) <= Cs(theta)+Co(theta)+Cc(theta)
    D <= [Cs+Co+Cc+Qhp*B]/A, 60 <= theta <100

Each evaluated point is a necessary upper; global minimizer certification is
not needed. All reported bounds are above the full HP carrier-flow minimum.
No HP duty can support demand above77C. Rearranging non-HP matches or mixing
does not create that high-grade heat under the same branch approaches. A
different HP outlet, additional upgrading or different source is a new route.

The worst declared thermal profile has isentropic4bar extraction,60C liquid
return, zero overhead plateau and136C compressor inlet. It minimizes every
cumulative source curve in the declared rectangle. Construction and dominance
support all profiles at the lower duty; one admissible worst profile supplies
an upper on common adaptive service. The rectangle is not a validated joint
steam/power/capture operating envelope; allocations are adaptive, not one HEN.

## Actual model witnesses

Nominal99.72%: inner35.979431152MW at0.05K, outer35.997588897MW at77C.
The36.5MW contract lacks0.289368818MW above77C; that is not the total service
shortfall, whose necessary lower bound is36.5-35.997588897=0.502411103MW.
The successful central ell=0.5 construction remains a counterexample to any
claim that all99.72% operation is infeasible.

Calibrated95%: inner36.811920166MW, outer36.822089093MW at60C. The constructed
lower supports36.5MW throughout the nominal thermal family. Scaling all thermal
duties/flows proportionally brackets its uniform derating limit between
0.847334680% and0.874717054%, an unresolved certificate band, not probability.
Nominal module electricity remains unchanged. These thermal contracts are not
assigned the central36.5MW cost/capture ledger.

The previous finite-grid failure upper is retained in a separate CSV column
and must not be represented as this continuum outer bound.

## Reproduction

The integrated runner computes the earlier continuous inner model before
certify_continuum_outer_cuts_r46_20261011.py reads its newly calculated lower
CSV. The outer calculation itself does not read that CSV to calculate its
source heat or upper capacity. verify_continuum_outer_cuts_r46_20261011.py
independently recomputes12point witnesses/72numeric fields from IF97 and printed
anchors without importing source curves or either allocator. The final
comparison then checks all25products against frozen references.
