# GNR605: Beed post-monsoon drought study

Updated 6 November 2026. All three requested research papers are present and reviewed. The user ran the first Andure-inspired October 2020 preview: VHI 91.43 over only 26.2% of the provisional district. The console result is archived, its consistency audit passes, and coverage diagnostics are ready to run. This is not yet a validated district-wide drought assessment.

The five-year pilot, historical audit, selected-pixel date audit and QA audit have been read. Numerical consistency checks pass. The remaining large exclusions are concentrated at the good-only SummaryQA gate. Allowing marginal observations greatly increases coverage, but their reliability is unverified. See [the QA findings](results/andure/qa_audit_review.md). Next run [the detailed quality profile](pipeline/andure/04_marginal_quality_profile_gee.js) before choosing a marginal-data policy. Corrected VHI and ML remain pending.

- [Start the Andure reconstruction](pipeline/andure/README.md): first-month Earth Engine script, explicit assumptions and CSV audit.

- [Critical paper review](literature/notes/paper_review.md): methods, findings, limitations and page references.
- [Literature matrix](literature/literature_matrix.md): comparable extraction fields and prioritized reading queue.
- [Proposed pilot and meeting brief](docs/project_proposal.md): research question, experiments, validation and team responsibilities.
- [Paper inventory](literature/papers/inventory.json): filenames, source identifiers, sizes and checksums.

## Source PDFs

1. Taji and Keskar: `literature/papers/1-s2.0-S221478532106449X-main.pdf`
2. Somni et al.: `literature/papers/aees-9-7-5.pdf`
3. Andure et al.: `literature/papers/Andure_et_al_2025_Beed_Drought_ML.pdf`

Current proposed scope: evaluate post-monsoon agricultural stress and the sensitivity of drought indicators to timing, thresholds and land-cover context. Novelty, general transferability and land degradation have not been established.
