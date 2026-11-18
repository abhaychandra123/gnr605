"""Evaluate the fixed October 2022 spatial holdout from rasters or saved site measurements."""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/reference"
RASTERS = ROOT / "data/landsat/processed"
BANDS = ("B3_green", "B4_red", "B5_nir", "B6_swir1", "B7_swir2")


def write_table(path, rows):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def raster_samples(sites, labels):
    import rasterio
    from rasterio.windows import Window

    rows = []
    with (rasterio.open(RASTERS / "october_2022_reflectance.tif") as spectral,
          rasterio.open(RASTERS / "october_2022_ndvi.tif") as ndvi):
        for site in sites:
            site_id = site["id"]
            if labels[site_id] == "unavailable":
                assert "asset_id" not in site
                continue
            chip = ROOT / "data/reference/chips" / f"{site_id}.tif"
            assert hashlib.sha256(chip.read_bytes()).hexdigest() == site["sha256"]
            if labels[site_id] == "uncertain":
                continue
            window = Window(site["col"], site["row"], 1, 1)
            values = spectral.read([3, 4, 5, 6, 7], window=window)[:, 0, 0].tolist()
            rows.append({"id": site_id, **dict(zip(BANDS, values)),
                         "ndvi": float(ndvi.read(1, window=window)[0, 0])})
    return rows


def confusion(rows, method):
    counts = Counter((r["green"], r[method]) for r in rows)
    tn, fp = counts[0, 0], counts[0, 1]
    fn, tp = counts[1, 0], counts[1, 1]
    green_recall, other_recall = tp / (tp + fn), tn / (tn + fp)
    return dict(tn=tn, fp=fp, fn=fn, tp=tp, accuracy=(tn + tp) / len(rows),
                green_recall=green_recall, other_recall=other_recall,
                balanced_accuracy=(green_recall + other_recall) / 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-samples", action="store_true",
                        help="Use the saved band measurements without opening satellite imagery.")
    args = parser.parse_args()
    label_path = OUT / "interpretation.csv"
    with label_path.open() as f:
        labels = {r["id"]: r["centre_interpretation"] for r in csv.DictReader(f)}
    sites = json.loads((OUT / "sites.json").read_text())
    locations = {s["id"]: s for s in sites}
    assert labels.keys() == locations.keys()
    sample_path = OUT / "samples.csv"
    if args.from_samples:
        with sample_path.open() as f:
            samples = list(csv.DictReader(f))
    else:
        samples = raster_samples(sites, labels)

    expected = {site_id for site_id, label in labels.items() if label in {"green", "water", "exposed"}}
    assert {s["id"] for s in samples} == expected and len(samples) == len(expected)
    rows = []
    for sample in samples:
        site = locations[sample["id"]]
        label = labels[site["id"]]
        features = [float(sample[band]) for band in BANDS]
        ndvi = float(sample["ndvi"])
        assert -1 <= ndvi <= 1 and all(math.isfinite(x) and x != -9999 for x in features)
        rows.append(dict(id=site["id"], split=site["split"], col=site["col"], row=site["row"],
                         green=int(label == "green"), reference=label, features=features,
                         ndvi=ndvi, baseline=int(ndvi > .30 + 1e-12)))
    train = [r for r in rows if r["split"] == "train"]
    test = [r for r in rows if r["split"] == "test"]
    assert min(r["col"] for r in test) - max(r["col"] for r in train) >= 400
    scales = []
    for j in range(len(BANDS)):
        mean = sum(r["features"][j] for r in train) / len(train)
        scales.append(math.sqrt(sum((r["features"][j] - mean) ** 2 for r in train) / len(train)))
    for row in test:
        distances = []
        for neighbour in train:
            # Centreing both vectors by the same training mean cancels in the difference.
            distance = sum(((a - b) / scale) ** 2
                           for a, b, scale in zip(row["features"], neighbour["features"], scales))
            distances.append((distance, neighbour["id"], neighbour["green"]))
        nearest = sorted(distances)[:3]
        row["knn"] = int(sum(c for _, _, c in nearest) >= 2)
        row["neighbours"] = " ".join(site_id for _, site_id, _ in nearest)

    stats = dict(sites=len(sites), labels=dict(Counter(labels.values())),
                 train=dict(Counter(r["reference"] for r in train)),
                 test=dict(Counter(r["reference"] for r in test)),
                 baseline=confusion(test, "baseline"), knn=confusion(test, "knn"),
                 standardized_distance_scales=scales,
                 same_decision=sum(r["knn"] == r["baseline"] for r in test),
                 nearest_train_test_metres=min(30 * math.hypot(t["row"] - r["row"], t["col"] - r["col"])
                                               for t in train for r in test),
                 labels_sha256=hashlib.sha256(label_path.read_bytes()).hexdigest())
    if not args.from_samples:
        write_table(sample_path, samples)
    write_table(OUT / "held_out_predictions.csv", test)
    (OUT / "evaluation.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(f'{len(train)} training sites, {len(test)} test sites. '
          f'NDVI agreement {stats["baseline"]["accuracy"]:.0%}, '
          f'three-nearest-neighbours agreement {stats["knn"]["accuracy"]:.0%}.')


if __name__ == "__main__":
    main()
