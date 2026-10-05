# Input-by-input reuse and attribution

Checked 5 October 2026. The software MIT license does not override these notices.
Original PDF/XLSX files and third-party database implementations are not bundled.

| Input | Source and actual basis | Released object and changes |
|---|---|---|
| Hagenholz monthly owner CSV | ERZ / Open Data Zürich, CC0: https://data.stadt-zuerich.ch/dataset/erz_abfallmenge_energie_khkw | Unchanged owner snapshot, retrieved 2 October 2026. Cleaner regenerates dates/calendar hours and unit-consistent monthly variables; CC0 origin retained. |
| Five-region heat proxy CSV | Matteo Giacomo Prina, PLANtoACT, https://doi.org/10.5281/zenodo.21834587 ; archived metadata `license.id=cc-by-4.0` | Changed: selected five regions, retained hour order, normalized/scaled shapes. Attribute Prina and identify these changes. Modeled profiles, not measurements. https://creativecommons.org/licenses/by/4.0/ |
| Capture catalogue numerical transcription | Danish Energy Agency and Energinet, February 2024 workbook: https://ens.dk/media/5729/download ; Index explicitly states CC BY 4.0 | Changed: selected sheet 401.a cells and source notes; unit/currency scope recorded. Catalogue benchmarks are not installed-project quotations. CC BY 4.0 attribution retained. |
| Storage catalogue numerical transcription | Danish Energy Agency and Energinet, July 2026 update: https://ens.dk/media/6589/download ; **Index C9** states Attribution 4.0 International | Changed: selected 141a/141b cells, converted losses/auxiliaries to fractions and investment to EUR2025 totals, added a zero-store case. This new direct check supersedes the old transcription's historically unconfirmed-license text; scientific values and its hash remain untouched. CC BY 4.0 attribution retained. |
| Joint residual-feed derived CSV | Vogt et al., UBA Texte 84/2023 and 86/2023. UBA official data-use notice: https://www.umweltbundesamt.de/en/disclaimer-privacy-policy-copyright , section C | Changed: source endpoint combination and extensive interpolation; synthetic coordinate, not observed annual composition. Official notice permits using/modifying/sharing data unless otherwise noted and requires source attribution plus identification of modifications. **No CC license is inferred for the full reports or all their contents.** Original reports are not bundled. |
| Herraiz 2026 process numerical card | Herraiz et al., https://doi.org/10.1016/j.ijggc.2026.104588 ; Supplement Table SM5.1 and Figure SM5.1 | Limited attributed numerical facts, source/version checks and project-written provenance only; no full article, supplement, source figure or reproduced page. The main accepted manuscript states CC BY, but no blanket supplementary-file reuse license is asserted. Third-party expression/figures remain with their rightsholders. |

Published Su (Fuel 2023, 126004) and Otgonbayar–Mazzotti (Energy 2024, 130087)
anchors in original code are attributed numerical states/equations, not copied
third-party implementation. Both source articles have CC BY 4.0 provenance in
the source audit. Source A is UK and source B Switzerland, both outside EU-27.

Generated numerical outputs and original artwork derive from the declared
inputs and original code. They are not primary observations and do not convert
upstream licenses into MIT. Retain upstream attribution and this notice when
sharing an archive. Responsible researchers must review license scope before
depositing a version; seek source clarification if intending broader reuse of
third-party expression. This record is provenance, not an individual legal opinion.
