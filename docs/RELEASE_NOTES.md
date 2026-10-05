# Prepared release 1.0.0 (local r40, 5 October 2026)

* Frozen scientific calculations and five r39 graphics remain the reference.
* A portable wrapper runs the original scientific stages from a new empty-results
  directory; the local computational-drive restriction is not exported as a
  requirement for other researchers' Windows computers.
* The storage reader no longer silently falls back to the originating machine's
  raw-data path. It requires the shipped numerical subset, or an explicit
  `PROJECT37_STORAGE_WORKBOOK` environment path for source revalidation.
* Six primary computational inputs retain their hashes and numerical values.
  The cleaned monthly CSV is regenerated rather than seeded into the pipeline.
* Source-specific data license evidence and a real data dictionary are added.
* Public code/data package excludes manuscript drafts, private correspondence,
  proprietary appendix, third-party full text and account credentials.
* Citation/DOI metadata is not fabricated; author metadata preparation is gated.

These changes address reproducibility and publication packaging, not new model
evidence, a new source-independent process case or closure of submission policy.
