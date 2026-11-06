# GNR605: Beed post-monsoon drought study

**Current assignment completed, 7 November 2026:** [ten-year October report](results/assignment/assignment_report.md), [year–area plot](results/assignment/year_vs_vegetation_area.png), and [reproduction instructions](pipeline/assignment/README.md).

The user clarified the required scope: select a drought-prone Indian area, download ten years of post-monsoon imagery, compute vegetation-covered area, and assess its year-to-year change. The completed assignment uses Beed and October 2015–2024: 43 downloaded MODIS images, seven spectral bands including infrared, and explicit local NDVI/classification/area calculations. On the fixed observable 65.7% of the district, cover is nearly stable at NDVI > 0.30, with four decreases and five increases. The larger apparent 2024 decline in raw observed area coincides with missing coverage. Computational validation passed; pixel-level field vegetation ground truth is unavailable.

**The extended yield/VHI/SPI work below is preserved as historical exploration. It does not define the current assignment or its next steps.**

**Corrected study completed 6 November 2026:** [results and limitations](results/study_corrected/research_results.md).
The official-boundary/cropland rerun retrieved and validated 1,056 Earth Engine rows,
harmonized 125 official crop records, and evaluated 30 simple indicator calibrations.
On the five 2020-2024 evaluation years, previous-year yield had lower MAE than every
indicator calibration. Better satellite coverage has not established crop-impact
forecasting skill. [Validation](results/study_corrected/validation.json) and
[comparison figure](results/study_corrected/holdout_error_comparison.png).

The earlier GAUL experiment below is retained as execution history; its lack of an
impact check was superseded by the corrected exploratory comparison above.

**Executed 6 November 2026:** [actual results and limitations](results/study/research_results.md).
The [controlled seasonal/rainfall pipeline](pipeline/study/README.md) ran on authenticated
Earth Engine: 120 comparison, 288 history and 528 rainfall rows were retrieved and
validated. SPI and figures are generated; all 12 tests pass. The original October
results reproduce exactly. Official boundary verification found a material mismatch:
8.56% of the provisional GAUL polygon is outside current official Beed. Crop-impact
validation and ML have not been performed. [Execution provenance](results/study/execution_manifest.json).

Updated 6 November 2026. All three requested research papers are present and reviewed. The user ran the first Andure-inspired October 2020 preview: VHI 91.43 over only 26.2% of the provisional district. The console result is archived, its consistency audit passes, and coverage diagnostics are ready to run. This is not yet a validated district-wide drought assessment.

The detailed quality profile was audited in full: 174 rows, all 54 expected composites, six joint quality patterns. Internal checks pass. Marginal observations include intermediate- and high-aerosol groups, with large differences between years. See [the full-file review](results/andure/detailed_quality_review.md) for verified denominators and the unresolved usefulness-code label. The screened sensitivity comparison has now executed; ML remains unrun.

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
