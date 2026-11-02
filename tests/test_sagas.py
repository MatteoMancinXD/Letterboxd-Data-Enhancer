import datetime
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import pandas as pd
import requests
from services import sagas_service as svc


TODAY = datetime.date(2026, 10, 31)

def film(title, year=2020, **extra):
    return dict(title=title, year=year, **extra)


def saga(films, sid='sample', **extra):
    return dict(id=sid, name=sid, category='saga', films=films, **extra)


class SagaTests(unittest.TestCase):
    def compute(self, definitions, library):
        with patch.object(svc, 'saga_catalog', return_value=definitions):
            result = svc.compute_sagas_progress(pd.DataFrame(library), today=TODAY)
        return result, result['started_sagas'] + result['completed_sagas'] + result['unstarted_sagas']

    def test_tmdb_average_includes_unwatched_and_excludes_missing_scores(self):
        result, items = self.compute([saga([film('One', tmdb_rating=8), film('Two', tmdb_rating=6), film('Three')])],
                                    [dict(Name='One', Year=2020, Rating=5, tmdb_rating=8)])
        self.assertEqual(items[0]['avg_tmdb_rating'], 7)
        self.assertEqual(items[0]['tmdb_ratings_count'], 2)
        self.assertEqual(items[0]['avg_user_rating'], 5)
        self.assertEqual(items[0]['taste_gap'], 2)
        self.assertEqual(items[0]['ratings_count'], 1)

    def test_future_and_unknown_dates_do_not_block_completion(self):
        _, items = self.compute([saga([film('One', release_date='2020-01-01'),
            film('Future', release_date='2027-01-01'), film('Unknown', release_date='')])],
            [dict(Name='One', Year=2020)])
        self.assertTrue(items[0]['is_complete'])
        self.assertEqual(items[0]['remaining_count'], 0)
        self.assertEqual(items[0]['upcoming_count'], 1)
        self.assertEqual(items[0]['unknown_release_count'], 1)

    def test_future_only_saga_is_not_completed_even_if_logged(self):
        _, items = self.compute([saga([film('Future', release_date='2027-01-01')])],
                               [dict(Name='Future', Year=2020)])
        self.assertFalse(items[0]['is_complete'])
        self.assertEqual(items[0]['progress_pct'], 0)

    def test_old_upcoming_flag_is_overridden_by_release_date(self):
        self.assertEqual(svc.release_state(film('One', upcoming=True, release_date='2025-01-01'), TODAY), 'released')
        self.assertEqual(svc.release_state(film('One', upcoming=True), TODAY), 'unknown')

    def test_unique_kpis_across_overlapping_universes(self):
        result, _ = self.compute([saga([film('One')], sid='a'), saga([film('One')], sid='b')],
                                [dict(Name='One', Year=2020, physical_copy=True)])
        self.assertEqual(result['kpis']['total_franchise_films_watched'], 1)
        self.assertEqual(result['kpis']['total_physical_films'], 1)

    def test_match_by_id_and_never_match_different_remake(self):
        lookup = svc.build_user_library_lookup(pd.DataFrame([dict(Name='Italian title', Year=2020, tmdb_id=42)]))
        self.assertIsNotNone(svc.match_film(film('English title', tmdb_id=42), lookup))
        lookup = svc.build_user_library_lookup(pd.DataFrame([dict(Name='Suspiria', Year=1977)]))
        self.assertIsNone(svc.match_film(film('Suspiria', year=2018), lookup))

    def test_tmdb_expands_standalone_saga_without_duplicate(self):
        curated = saga([film('One'), film('Two')])
        collection = saga([film('One'), film('Two'), film('Three')], sid='tmdb_col_10')
        with patch.object(svc, 'CURATED_SAGAS', [curated]), patch.object(svc, 'read_cache', side_effect=[[], [collection]]):
            catalog = svc.saga_catalog()
        self.assertEqual(len(catalog), 1)
        self.assertEqual(len(catalog[0]['films']), 3)
        self.assertEqual(catalog[0]['source'], 'tmdb')

    def test_collection_is_not_used_as_entire_universe(self):
        universe = saga([film('One'), film('Two')])
        universe['category'] = 'universe'
        collection = saga([film('One'), film('Two'), film('Three')], sid='tmdb_col_10')
        with patch.object(svc, 'CURATED_SAGAS', [universe]), patch.object(svc, 'read_cache', side_effect=[[], [collection]]):
            catalog = svc.saga_catalog()
        self.assertEqual(len(catalog), 2)
        self.assertEqual(len(catalog[0]['films']), 2)

    def test_scan_refreshes_existing_collection_once_and_caches_ratings(self):
        response = Mock()
        response.json.return_value = dict(name='Series', parts=[dict(id=1, title='One', vote_average=8, vote_count=20, release_date='2020-01-01')])
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = str(Path(directory) / 'cache.json')
            svc.write_cache(path, [saga([film('Old')], sid='tmdb_col_10')])
            with patch.object(svc, 'CACHE_FILE', path), patch.object(svc, 'get_tmdb_api_key', return_value='test'), patch.object(svc.requests, 'get', return_value=response) as get:
                report = svc.scan_and_cache_tmdb_collections(pd.DataFrame([dict(collection_id=10), dict(collection_id=10)]))
            self.assertEqual(report['refreshed'], 1)
            self.assertEqual(get.call_count, 1)
            self.assertEqual(svc.read_cache(path)[0]['films'][0]['tmdb_rating'], 8)

    def test_missing_universe_film_can_be_added_and_survives_reload(self):
        universe = saga([film('One')])
        universe['category'] = 'universe'
        details = dict(title='Two', year=2026, tmdb_id=22, release_date='2026-06-01', tmdb_rating=8)
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = str(Path(directory) / 'curated.json')
            with patch.object(svc, 'CURATED_SAGAS', [universe]), patch.object(svc, 'CURATED_CACHE_FILE', path), patch.object(svc, 'get_tmdb_api_key', return_value='test'), patch.object(svc, 'fetch_movie_details_by_id', return_value=details):
                self.assertTrue(svc.add_film_to_curated_saga('sample', 22, 'Phase 2'))
                self.assertFalse(svc.add_film_to_curated_saga('sample', 22))
                loaded = svc.saga_catalog(False)
            self.assertEqual(len(loaded[0]['films']), 2)
            self.assertEqual(loaded[0]['films'][1]['phase'], 'Phase 2')

    def test_failed_curated_refresh_does_not_claim_success(self):
        with patch.object(svc, 'saga_catalog', return_value=[saga([film('One')])]), patch.object(svc, 'get_tmdb_api_key', return_value='test'), patch.object(svc, 'fetch_movie_metadata', return_value=None), patch.object(svc, 'write_cache') as save:
            report = svc.refresh_curated_saga('sample')
        self.assertEqual(report, dict(updated=0, failed=1))
        save.assert_not_called()

    def test_halloween_remakes_are_distinct_and_recognized(self):
        from services.sagas_catalog import EXTRA_SAGAS
        halloween = next(s for s in EXTRA_SAGAS if s['id'] == 'halloween')
        _, items = self.compute([halloween], [dict(Name='Halloween', Year=1978, Rating=5), dict(Name='Halloween', Year=2018, Rating=3)])
        self.assertEqual(items[0]['total_films'], 13)
        self.assertEqual(items[0]['watched_count'], 2)
        self.assertEqual(items[0]['remaining_count'], 11)

    def test_thematic_aliases_and_original_oldboy(self):
        from services.sagas_catalog import EXTRA_SAGAS
        dollars = next(s for s in EXTRA_SAGAS if s['id'] == 'dollars')
        vengeance = next(s for s in EXTRA_SAGAS if s['id'] == 'vengeance')
        _, items = self.compute([dollars, vengeance], [dict(Name='Per un pugno di dollari', Year=1964, Rating=4), dict(Name='Oldboy', Year=2013, Rating=3)])
        indexed = {s['id']: s for s in items}
        self.assertEqual(indexed['dollars']['watched_count'], 1)
        self.assertEqual(indexed['vengeance']['watched_count'], 0)
        self.assertEqual(indexed['dollars']['category'], 'thematic')

    def test_catalog_has_unique_ids_and_film_entries(self):
        self.assertEqual(len(svc.CURATED_SAGAS), len({s['id'] for s in svc.CURATED_SAGAS}))
        for item in svc.CURATED_SAGAS:
            self.assertEqual(len(item['films']), len({svc.film_key(f) for f in item['films']}), item['id'])

    def test_scan_failure_keeps_cache(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = str(Path(directory) / 'cache.json')
            svc.write_cache(path, [saga([film('Old')], sid='tmdb_col_10')])
            before = Path(path).read_bytes()
            with patch.object(svc, 'CACHE_FILE', path), patch.object(svc, 'get_tmdb_api_key', return_value='test'), patch.object(svc.requests, 'get', side_effect=requests.Timeout):
                report = svc.scan_and_cache_tmdb_collections(pd.DataFrame([dict(collection_id=10)]))
            self.assertEqual(report['failed'], 1)
            self.assertEqual(before, Path(path).read_bytes())


if __name__ == '__main__':
    unittest.main()
