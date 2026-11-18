"""Identify which Octobers limit the comparable ten-year MODIS footprint."""
import csv
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[2]
RASTERS = ROOT / "data/assignment/processed"
RESULTS = ROOT / "results/assignment"


def main():
    with (RESULTS / "year_vs_vegetation_area.csv").open() as f:
        annual = list(csv.DictReader(f))
    years = [int(r["year"]) for r in annual]
    with rasterio.open(RASTERS / "district_mask.tif") as src:
        district = src.read(1)
        grid = (src.shape, src.crs, src.transform)
        pixel_area = abs(src.transform.a * src.transform.e) / 1e6
    counts = []
    for year in years:
        with rasterio.open(RASTERS / f"october_{year}_observations.tif") as src:
            assert (src.shape, src.crs, src.transform) == grid
            counts.append(src.read(1))
    with rasterio.open(RASTERS / "common_valid_min1.tif") as src:
        assert (src.shape, src.crs, src.transform) == grid
        recorded_common = src.read(1)

    # A pixel enters a nine-year intersection only if the omitted year was its only gap.
    district_pixels, common = 0, 0
    only_gap = [0] * len(years)
    for row in range(district.shape[0]):
        for col in range(district.shape[1]):
            if district[row, col] != 1:
                continue
            district_pixels += 1
            missing = [i for i, image in enumerate(counts) if image[row, col] == 0]
            assert bool(recorded_common[row, col]) == (len(missing) == 0)
            if not missing:
                common += 1
            elif len(missing) == 1:
                only_gap[missing[0]] += 1
    assert common == int(annual[0]["common_pixels"])
    assert district_pixels == int(annual[0]["district_pixels"])
    with (RESULTS / "coverage_by_omitted_year.csv").open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["omitted_year", "district_pixels", "ten_year_common_pixels",
                         "pixels_missing_only_in_omitted_year", "nine_year_common_pixels",
                         "nine_year_common_km2", "nine_year_common_pct"])
        for year, additional in zip(years, only_gap):
            nine_year = common + additional
            writer.writerow([year, district_pixels, common, additional, nine_year,
                             nine_year * pixel_area, 100 * nine_year / district_pixels])


if __name__ == "__main__":
    main()
