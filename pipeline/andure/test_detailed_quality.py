"""Check that the quality auditor actually rejects corrupt/incomplete exports."""
import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import analyze_detailed_quality as audit


class DetailedQualityAuditTests(unittest.TestCase):
    def run_case(self, mutate, should_fail):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for name in ['detailed_quality_input_extract.json', 'date_audit_input_extract.json', 'qa_audit_input_extract.json']:
                (target / name).write_text((audit.OUT / name).read_text())
            source_path = target / 'detailed_quality_input_extract.json'
            source = json.loads(source_path.read_text())
            rows = list(csv.DictReader(io.StringIO(source['csv_text'])))
            mutate(rows)
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            source['csv_text'] = buffer.getvalue()
            source['provenance']['reader_total_lines'] = len(rows) + 1
            source_path.write_text(json.dumps(source))
            with patch.object(audit, 'OUT', target), redirect_stdout(io.StringIO()):
                if should_fail:
                    with self.assertRaises(SystemExit):
                        audit.main()
                else:
                    audit.main()

    def test_real_export_passes(self):
        self.run_case(lambda rows: None, False)

    def test_wrong_decoded_aerosol_rejected(self):
        self.run_case(lambda rows: rows[0].update(aerosol='3'), True)

    def test_missing_composite_rejected(self):
        def remove(rows):
            day = rows[0]['source_start']
            rows[:] = [r for r in rows if r['source_start'] != day]
        self.run_case(remove, True)

    def test_wrong_area_rejected(self):
        self.run_case(lambda rows: rows[0].update(area_km2='1'), True)


if __name__ == '__main__':
    unittest.main()
