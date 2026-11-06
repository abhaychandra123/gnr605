"""Poll submitted tasks and retrieve their uniquely matched Drive CSVs."""
import argparse
import csv
import hashlib
import io
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ee
from google.auth.exceptions import TransportError
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from execute_ee import EXPECTED, NAMES, ROOT, atomic_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    parser.add_argument('--input-dir', type=Path, default=ROOT / 'data/study')
    parser.add_argument('--cancel-redundant', action='store_true',
                        help='After all local exports pass validation, cancel only these recorded jobs')
    args = parser.parse_args()
    if args.cancel_redundant:
        from analysis import check_comparison, check_history, screened_bounds, load_rainfall
        check_comparison(args.input_dir / (NAMES['comparison'] + '.csv'))
        check_history(args.input_dir / (NAMES['history'] + '.csv'), screened_bounds())
        load_rainfall(args.input_dir / (NAMES['rainfall'] + '.csv'))
    for attempt in range(3):
        try:
            ee.Initialize(project=args.project)
            break
        except TransportError:
            if attempt == 2:
                raise
            time.sleep(3)
    drive = build('drive', 'v3', credentials=ee.data.get_persistent_credentials(), cache_discovery=False)
    statuses = {}
    for stage, name in NAMES.items():
        manifest_path = args.input_dir / 'tasks' / f'{name}.json'
        if not manifest_path.exists():
            statuses[stage] = {'state': 'NOT_SUBMITTED'}
            continue
        manifest = json.loads(manifest_path.read_text())
        status = ee.data.getTaskStatus(manifest['task_id'])[0]
        statuses[stage] = status
        print(f"{stage}: {status['state']}", flush=True)
        if args.cancel_redundant and status['state'] in ('READY', 'RUNNING'):
            ee.data.cancelTask(manifest['task_id'])
            statuses[stage] = ee.data.getTaskStatus(manifest['task_id'])[0]
            print(f'Cancelled redundant {stage} batch job after validating local results', flush=True)
            continue
        if status.get('error_message'):
            print(status['error_message'], flush=True)
        if status['state'] != 'COMPLETED':
            continue
        destination = args.input_dir / f'{name}.csv'
        if destination.exists():
            print(f'Preserving existing {destination}', flush=True)
            continue
        after = (datetime.fromisoformat(manifest['submitted_utc']) - timedelta(minutes=1)).isoformat()
        listing = drive.files().list(
            q=f"trashed = false and name = '{name}.csv' and createdTime > '{after}'",
            fields='files(id,name,size,md5Checksum,createdTime,parents),nextPageToken', pageSize=100).execute(num_retries=3)
        files = listing.get('files', [])
        if listing.get('nextPageToken') or len(files) != 1:
            raise RuntimeError(f'Expected one new Drive file for {stage}; found {len(files)}')
        metadata = files[0]
        payload = io.BytesIO()
        downloader = MediaIoBaseDownload(payload, drive.files().get_media(fileId=metadata['id']))
        done = False
        while not done:
            _, done = downloader.next_chunk(num_retries=3)
        raw = payload.getvalue()
        if metadata.get('md5Checksum') and hashlib.md5(raw).hexdigest() != metadata['md5Checksum']:
            raise ValueError('Download checksum mismatch')
        rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        if len(rows) != EXPECTED[stage]:
            raise ValueError(f'Unexpected {stage} row count: {len(rows)}')
        temporary = destination.with_suffix('.csv.tmp')
        temporary.write_bytes(raw)
        temporary.replace(destination)
        atomic_json(destination.with_suffix('.provenance.json'), {
            'drive': metadata, 'task': manifest, 'task_status': status,
            'sha256': hashlib.sha256(raw).hexdigest(), 'rows': len(rows),
            'retrieved_utc': datetime.now(timezone.utc).isoformat()})
        print(f'Downloaded {len(rows)} rows to {destination}', flush=True)
    atomic_json(args.input_dir / 'task_status.json', statuses)


if __name__ == '__main__':
    main()
