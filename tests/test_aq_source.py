"""Offline regression tests for the live publisher feed adapter."""
import copy
import csv
import json
import tempfile
import importlib.util
import pathlib
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('fetch_aq', ROOT / 'scripts/fetch-aq-latest.py')
aq = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(aq)


def sample():
    return {'countryId': 'India', 'country': [
        {'stateId': 'Example State', 'citiesInState': [
            {'cityId': 'Example City', 'stationsInCity': [
                {'stationName': 'Example Station', 'siteId': 'site_example',
                 'latitude': 20, 'longitude': 77, 'lastUpdate': '10-11-2026 04:00:00',
                 'pollutants': [{'indexId': 'CO', 'min': '19', 'max': '28',
                                 'avg': '24', 'Hourly_sub_index': '27'}]}]}]}]}


class PublisherTests(unittest.TestCase):
    def test_flatten_keeps_original_values_and_observation_time(self):
        row, = aq.parse_cpcb(sample())
        self.assertEqual(row['avg_value'], '24')
        self.assertEqual(row['last_update'], '10-11-2026 04:00:00')
        self.assertEqual(row['station'], 'Example Station')
        self.assertEqual(row['country'], 'India')
        cities = [{'id': 'example', 'name': 'Example City', 'state': 'Example State'}]
        pollutants, _, updated, _, _, _ = aq.aggregate([row], cities)
        self.assertEqual(pollutants['CO']['example'], 0.48)
        self.assertEqual(updated, '2026-11-10T04:00:00+05:30')

    def test_missing_values_stay_missing(self):
        payload = sample()
        payload['country'][0]['citiesInState'][0]['stationsInCity'][0]['pollutants'][0]['avg'] = 'NA'
        rows = aq.parse_cpcb(payload)
        self.assertEqual(rows[0]['avg_value'], 'NA')
        self.assertIsNone(aq.to_float(rows[0]['avg_value']))

    def test_empty_and_malformed_responses_fail(self):
        for payload in ({}, [], {'countryId': 'India', 'country': []},
                        {'countryId': 'India', 'country': [{'stateId': 'X'}]}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                aq.parse_cpcb(payload)

    def test_bad_coordinates_timestamps_and_duplicate_rows_fail(self):
        for key, value in [('latitude', 'NaN'), ('longitude', 181),
                           ('lastUpdate', 'yesterday'), ('stationName', '')]:
            payload = sample()
            payload['country'][0]['citiesInState'][0]['stationsInCity'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                aq.parse_cpcb(payload)
        payload = sample()
        station = payload['country'][0]['citiesInState'][0]['stationsInCity'][0]
        station['pollutants'].append(copy.deepcopy(station['pollutants'][0]))
        with self.assertRaises(ValueError):
            aq.parse_cpcb(payload)

    def test_mixed_age_rows_are_filtered_before_aggregation(self):
        rows = aq.parse_cpcb(sample())
        stale = dict(rows[0], station='Old Station', avg_value='500',
                     last_update='16-10-2026 19:00:00')
        now = datetime(2026, 11, 9, 23, tzinfo=timezone.utc)
        current = aq.fresh_rows(rows + [stale], now)
        self.assertEqual(current, rows)
        cities = [{'id': 'example', 'name': 'Example City', 'state': 'Example State'}]
        pollutants, _, _, _, _, _ = aq.aggregate(current, cities)
        self.assertEqual(pollutants['CO']['example'], 0.48)

    def test_freshness_cutoff_is_inclusive_and_uses_ist(self):
        row = aq.parse_cpcb(sample())[0]
        now = datetime(2026, 11, 9, 23, tzinfo=timezone.utc)
        boundary = dict(row, last_update='09-11-2026 22:30:00')
        too_old = dict(row, last_update='09-11-2026 22:29:59')
        self.assertEqual(aq.fresh_rows([boundary, too_old], now), [boundary])
        with self.assertRaises(ValueError):
            aq.fresh_rows([too_old], now)

    def test_missing_malformed_or_future_timestamps_fail(self):
        row = aq.parse_cpcb(sample())[0]
        now = datetime(2026, 11, 9, 23, tzinfo=timezone.utc)
        for stamp in (None, '', 'yesterday', '10-11-2026 05:30:01'):
            invalid = dict(row, last_update=stamp)
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                aq.fresh_rows([row, invalid], now)
        missing = dict(row)
        missing.pop('last_update')
        with self.assertRaises(ValueError):
            aq.fresh_rows([row, missing], now)
        with self.assertRaises(ValueError):
            aq.fresh_rows([], now)

    def test_main_excludes_stale_rows_from_latest_and_raw_snapshot(self):
        now = datetime.now(aq.IST)
        fresh = aq.parse_cpcb(sample())[0]
        fresh['last_update'] = now.strftime('%d-%m-%Y %H:%M:%S')
        stale = dict(fresh, station='Old Station', avg_value='500',
                     last_update=(now - timedelta(hours=7)).strftime('%d-%m-%Y %H:%M:%S'))
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            data = root / 'docs/projects/air-quality/data'
            data.mkdir(parents=True)
            (data / 'cities.json').write_text(json.dumps([
                {'id': 'example', 'name': 'Example City', 'state': 'Example State'}]))
            (data / 'stations.json').write_text('[]')
            with patch.object(aq, '__file__', str(root / 'scripts/fetch-aq-latest.py')), \
                 patch.object(aq, 'fetch_cpcb', return_value=([fresh, stale], 2)), \
                 patch('sys.argv', ['fetch-aq-latest.py', '--snapshot-dir', 'snapshots']):
                aq.main()
            latest = json.loads((data / 'latest.json').read_text())
            self.assertEqual(latest['pollutants']['CO']['example'], 0.48)
            snapshot, = (root / 'snapshots').glob('*.csv')
            with snapshot.open() as handle:
                saved = list(csv.DictReader(handle))
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]['station'], 'Example Station')
            self.assertEqual(saved[0]['last_update'], fresh['last_update'])

    def test_network_error_never_changes_published_files(self):
        latest = ROOT / 'docs/projects/air-quality/data/latest.json'
        before = latest.read_bytes()
        with patch.object(aq, 'fetch_cpcb', side_effect=OSError('unavailable')), \
             patch('sys.argv', ['fetch-aq-latest.py']), self.assertRaises(SystemExit):
            aq.main()
        self.assertEqual(latest.read_bytes(), before)

    def test_incomplete_mirror_never_changes_published_files(self):
        latest = ROOT / 'docs/projects/air-quality/data/latest.json'
        before = latest.read_bytes()
        rows = aq.parse_cpcb(sample())
        with patch.object(aq, 'fetch_all', return_value=(rows, 2)), \
             patch('sys.argv', ['fetch-aq-latest.py', '--source', 'data-gov',
                                '--key', 'test-key']), self.assertRaises(SystemExit):
            aq.main()
        self.assertEqual(latest.read_bytes(), before)

    def test_stale_payload_never_changes_published_files(self):
        payload = sample()
        payload['country'][0]['citiesInState'][0]['stationsInCity'][0].update({
            'lastUpdate': '16-10-2026 19:00:00',
            'stationName': 'Alipur, Delhi - DPCC'})
        payload['country'][0]['stateId'] = 'Delhi'
        payload['country'][0]['citiesInState'][0]['cityId'] = 'Delhi'
        rows = aq.parse_cpcb(payload)
        latest = ROOT / 'docs/projects/air-quality/data/latest.json'
        before = latest.read_bytes()
        with patch.object(aq, 'fetch_cpcb', return_value=(rows, len(rows))), \
             patch('sys.argv', ['fetch-aq-latest.py']), self.assertRaises(SystemExit):
            aq.main()
        self.assertEqual(latest.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
