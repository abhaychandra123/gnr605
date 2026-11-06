"""Download public official ancillary data, preserving sources and retrieval hashes."""
import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / 'data/study/ancillary'


def boundary():
    url = 'https://surveyofindia.gov.in/documents/State_District_Subdistrict_PAN%20INDIA.rar'
    path = FOLDER / 'soi_complete.rar'
    session = requests.Session()
    head = session.head(url, timeout=30)
    head.raise_for_status()
    size = int(head.headers['Content-Length'])
    while not path.exists() or path.stat().st_size < size:
        start = path.stat().st_size if path.exists() else 0
        end = min(start + 4 * 1024 * 1024 - 1, size - 1)
        for attempt in range(4):
            try:
                r = session.get(url, headers={'Range': f'bytes={start}-{end}'}, timeout=60)
                r.raise_for_status()
                if r.status_code != 206 or not r.headers.get('Content-Range', '').startswith(f'bytes {start}-'):
                    raise ValueError('Server did not honor requested byte range')
                if len(r.content) != end - start + 1:
                    raise ValueError('Incomplete range')
                with path.open('ab') as stream:
                    stream.write(r.content)
                break
            except (requests.RequestException, ValueError):
                if attempt == 3:
                    raise
                time.sleep(2)
        print(f'Official boundaries: {path.stat().st_size}/{size} bytes', flush=True)
    provenance = {'url': url, 'last_modified': head.headers.get('Last-Modified'), 'bytes': size,
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                  'retrieved_utc': datetime.now(timezone.utc).isoformat()}
    path.with_suffix('.provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')


def crops():
    url = 'https://krishi.maharashtra.gov.in/Site/Common/ViewGr.aspx?Doctype=01ce19af-d065-4817-ac1a-71c1c0f8874d'
    session = requests.Session()
    response = session.get(url, timeout=45)
    response.raise_for_status()
    manifest = []
    for page in range(1, 7):
        (FOLDER / f'apy_listing_page_{page}.html').write_text(response.text)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find(id='SitePH_grdupload')
        if table is None:
            raise ValueError('Official APY listing table missing')
        for a in table.find_all('a', href=True):
            href = a['href']
            if not href.lower().endswith('.pdf'):
                continue
            file_url = quote(urljoin(url, href), safe=':/%')
            year = re.search(r'(20\d{2})[-_](\d{2})', href)
            if not year:
                continue
            if int(year[1]) > 2024:
                continue  # Multiple forecast vintages exist; outside this study.
            name = f'official_apy_{year[1]}_{year[2]}.pdf'
            path = FOLDER / name
            if not path.exists():
                r = session.get(file_url, timeout=60)
                r.raise_for_status()
                if not r.content.startswith(b'%PDF'):
                    raise ValueError('Expected PDF from official APY link')
                path.write_bytes(r.content)
            manifest.append({'file': name, 'url': file_url, 'year': f'{year[1]}-{year[2]}',
                             'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            print(f'Acquired {name}', flush=True)
        if page == 6:
            break
        fields = {i['name']: i.get('value', '') for i in soup.find_all('input', attrs={'name': True})
                  if i.get('type') not in ('submit', 'button', 'image')}
        for select in soup.find_all('select', attrs={'name': True}):
            selected = select.find('option', selected=True) or select.find('option')
            if selected:
                fields[select['name']] = selected.get('value', '')
        nxt = soup.find(id='SitePH_grdupload_btnNext')['href']
        target = re.search(r"__doPostBack\('([^']+)'", nxt)[1]
        fields.update(__EVENTTARGET=target, __EVENTARGUMENT='')
        response = session.post(url, data=fields, timeout=60)
        response.raise_for_status()
    (FOLDER / 'crop_source_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['boundary', 'crops'])
    args = parser.parse_args()
    FOLDER.mkdir(parents=True, exist_ok=True)
    (boundary if args.stage == 'boundary' else crops)()
