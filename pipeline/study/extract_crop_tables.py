"""Extract Beed rows with source units retained; no impact inference or imputation."""
import csv
import json
import re
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'data/study/ancillary'
rows, issues = [], []
for path in sorted(FOLDER.glob('official_apy_*.pdf')):
    year = int(path.stem.split('_')[2])
    if year > 2024:
        continue
    with pdfplumber.open(path) as document:
        for page_number, page in enumerate(document.pages, 1):
            text = page.extract_text() or ''
            title = '\n'.join(text.splitlines()[:3])
            units = '\n'.join(line for line in text.splitlines() if any(
                word in line.lower() for word in ['area in', 'tonnes', 'bales', 'productivity', 'production in']))
            for table in page.extract_tables():
                header_index = next((i for i, r in enumerate(table[:5]) if 'District' in r), None)
                if header_index is None:
                    continue
                header = table[header_index]
                district_index = header.index('District')
                for row in table[header_index + 2:]:
                    district_cell = row[district_index] or ''
                    districts = district_cell.split('\n')
                    if 'Beed' not in districts:
                        continue
                    take = districts.index('Beed')
                    for i in range(district_index + 1, len(header), 3):
                        crop = (header[i] or '').replace('\n', ' ')
                        if not crop or i + 2 >= len(row):
                            continue
                        values = []
                        for cell in row[i:i + 3]:
                            values_by_district = (cell or '').split('\n')
                            if len(values_by_district) != len(districts):
                                issues.append({'file': path.name, 'page': page_number, 'crop': crop,
                                               'issue': 'Merged-cell row alignment is ambiguous', 'cell': cell})
                                values = []
                                break
                            values.append(values_by_district[take])
                        if len(values) != 3:
                            continue
                        rows.append({'start_year': year, 'agricultural_year': f'{year}-{str(year+1)[-2:]}',
                                     'district': 'Beed', 'crop_label_source': crop,
                                     'area_raw': values[0], 'production_raw': values[1], 'yield_raw': values[2],
                                     'source_file': path.name, 'source_page': page_number,
                                     'source_title': title, 'units_and_footnotes': units,
                                     'status': 'source_units_preserved_not_impact_validated'})
    print(f'Extracted {path.name}; cumulative rows={len(rows)}', flush=True)
out = ROOT / 'results/study'
with (out / 'beed_crop_statistics_raw.csv').open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
(out / 'crop_extraction_issues.json').write_text(json.dumps(issues, indent=2) + '\n')
print(f'{len(rows)} source rows; {len(issues)} ambiguous cells retained in issue log')
