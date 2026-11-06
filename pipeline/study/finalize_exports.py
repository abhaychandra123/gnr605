"""Create content-addressed provenance for checkpointed real Earth Engine results."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from analysis import check_comparison, check_history, load_rainfall, screened_bounds
from execute_ee import ROOT, NAMES, EXPECTED, atomic_json

folder = ROOT / 'data/study'
check_comparison(folder / (NAMES['comparison'] + '.csv'))
check_history(folder / (NAMES['history'] + '.csv'), screened_bounds())
load_rainfall(folder / (NAMES['rainfall'] + '.csv'))
manifest = {'completed_utc': datetime.now(timezone.utc).isoformat(),
            'project': 'weighttrack-493810', 'retrieval': 'official ee.data.computeFeatures',
            'scope': 'Controlled comparison on provisional GAUL 2015; not independent impact validation',
            'exports': {}}
for stage, name in NAMES.items():
    path = folder / f'{name}.csv'
    raw = path.read_bytes()
    checkpoints = sorted((folder / 'checkpoints' / stage).glob('*.json'))
    saved = [json.loads(p.read_text()) for p in checkpoints]
    rows = [row for data in saved for row in data['rows']]
    hashes = {data['script_sha256'] for data in saved}
    if len(rows) != EXPECTED[stage] or len(hashes) != 1:
        raise ValueError(f'Checkpoint provenance is incomplete for {stage}')
    with path.open(newline='') as stream:
        actual = list(csv.DictReader(stream))
    # Compare canonical values with the exact dictionaries received from EE.
    expected = [{k: '' if row.get(k) is None else str(row.get(k, '')) for k in actual[0]} for row in rows]
    if actual != expected:
        raise ValueError(f'Final CSV differs from checkpoint records: {stage}')
    source = folder / 'tasks/direct_executor.py'
    if hashlib.sha256(source.read_bytes()).hexdigest() not in hashes:
        raise ValueError('Archived direct executor does not match computation hash')
    record = {'rows': len(rows), 'sha256': hashlib.sha256(raw).hexdigest(),
              'script_sha256': next(iter(hashes)), 'checkpoints': len(checkpoints),
              'first_retrieved_utc': min(v['retrieved_utc'] for v in saved),
              'last_retrieved_utc': max(v['retrieved_utc'] for v in saved),
              'method': 'official_earth_engine_computeFeatures', 'project': manifest['project']}
    atomic_json(path.with_suffix('.provenance.json'), record)
    manifest['exports'][stage] = record
atomic_json(ROOT / 'results/study/execution_manifest.json', manifest)
print(json.dumps(manifest, indent=2))
