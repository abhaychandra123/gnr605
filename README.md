# GNR605: Beed post-monsoon drought study

**Current execution handoff:** [autonomous continuation and access setup](docs/AUTONOMOUS_HANDOFF.md).
The [controlled seasonal/rainfall pipeline](pipeline/study/README.md) is implemented
as a GEE export script plus local analysis, with seven statistical tests passing.
New satellite jobs remain unexecuted because this session lacks network/authentication.
Actual screened-NDVI coverage bounds are saved in `results/study/screened_coverage_bounds.csv`;
they are derived from existing real exports, not new satellite downloads.

Updated 6 November 2026. All three requested research papers are present and reviewed. The user ran the first Andure-inspired October 2020 preview: VHI 91.43 over only 26.2% of the provisional district. The console result is archived, its consistency audit passes, and coverage diagnostics are ready to run. This is not yet a validated district-wide drought assessment.

The detailed quality profile has now been audited in full: 174 rows, all 54 expected composites, six joint quality patterns. Internal checks pass. Marginal observations include intermediate- and high-aerosol groups, with large differences between years. See [the full-file review](results/andure/detailed_quality_review.md) for verified denominators, the unresolved usefulness-code label, and a proposed screened sensitivity comparison. That comparison, corrected VHI and ML remain pending.

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
