import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from services.importer_service import load_uploaded_files, merge_letterboxd_dfs, compute_dataset_diff, apply_dataset_update, save_dataset


class Upload(io.BytesIO):
    def __init__(self, name, content):
        super().__init__(content)
        self.name = name


def frame(rows):
    return pd.DataFrame(rows)


def movie(name='Alien', year=1979, rating=4, **extra):
    return dict(Name=name, Year=year, Rating=rating, **extra)


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.existing = frame([movie(physical_copy=True, tmdb_id=348, genres=['Horror']), movie('Aliens', 1986, 3)])

    def test_partial_rating_changes_preserve_other_films_and_metadata(self):
        incoming = merge_letterboxd_dfs({'ratings.csv': frame([movie(rating=5)])})
        added, deleted, retained = compute_dataset_diff(self.existing, incoming)
        self.assertTrue(added.empty and deleted.empty)
        self.assertEqual(len(retained), 2)
        self.assertEqual(retained.iloc[0]['Rating'], 5)
        self.assertEqual(retained.iloc[0]['tmdb_id'], 348)
        self.assertEqual(retained.iloc[0]['genres'], ['Horror'])
        self.assertTrue(retained.iloc[0]['physical_copy'])
        self.assertEqual(len(retained.attrs['rating_changes']), 1)

    def test_watched_without_rating_column_preserves_rating(self):
        incoming = merge_letterboxd_dfs({'watched.csv': frame([{'Name': 'Alien', 'Year': 1979}])})
        _, removed, retained = compute_dataset_diff(self.existing, incoming)
        self.assertEqual(len(removed), 1)
        self.assertEqual(retained.iloc[0]['Rating'], 4)

    def test_full_export_removed_rating_is_not_restored_from_diary(self):
        incoming = merge_letterboxd_dfs({
            'watched.csv': frame([{'Name': 'Alien', 'Year': 1979}]),
            'ratings.csv': pd.DataFrame(columns=['Name', 'Year', 'Rating']),
            'diary.csv': frame([movie(rating=4.5)])})
        _, _, retained = compute_dataset_diff(self.existing, incoming)
        self.assertTrue(pd.isna(retained.iloc[0]['Rating']))
        self.assertEqual(len(retained.attrs['rating_changes']), 1)

    def test_blank_partial_rating_clears_only_that_film(self):
        incoming = merge_letterboxd_dfs({'ratings.csv': frame([movie(rating=None)])})
        _, removed, retained = compute_dataset_diff(self.existing, incoming)
        self.assertTrue(removed.empty)
        self.assertTrue(pd.isna(retained.iloc[0]['Rating']))
        self.assertEqual(retained.iloc[1]['Rating'], 3)

    def test_latest_diary_date_wins_not_row_order(self):
        incoming = merge_letterboxd_dfs({'diary.csv': frame([
            movie(rating=2, **{'Watched Date': '2026-09-20'}),
            movie(rating=5, **{'Watched Date': '2020-01-01'})])})
        self.assertEqual(len(incoming), 1)
        self.assertEqual(incoming.iloc[0]['Rating'], 2)
        self.assertEqual(incoming.iloc[0]['Date'], '2026-09-20')

    def test_latest_blank_diary_rating_not_previous_rating(self):
        incoming = merge_letterboxd_dfs({'diary.csv': frame([
            movie(rating=5, **{'Watched Date': '2020-01-01'}),
            movie(rating=None, **{'Watched Date': '2026-09-20'})])})
        self.assertTrue(pd.isna(incoming.iloc[0]['Rating']))

    def test_ratings_override_diary_even_for_diary_only_base(self):
        incoming = merge_letterboxd_dfs({'ratings.csv': frame([movie(rating=2)]),
                                        'diary.csv': frame([movie(rating=5)])})
        self.assertEqual(incoming.iloc[0]['Rating'], 2)

    def test_same_title_remakes_never_collapsed(self):
        existing = frame([movie('Suspiria', 1977, 4)])
        incoming = merge_letterboxd_dfs({'diary.csv': frame([movie('Suspiria', 2018, 5)])})
        added, removed, retained = compute_dataset_diff(existing, incoming)
        self.assertEqual(len(added), 1)
        self.assertEqual(len(retained), 1)
        self.assertTrue(removed.empty)

    def test_uri_matches_changed_title(self):
        existing = frame([movie(**{'Letterboxd URI': 'https://letterboxd.com/film/alien/'})])
        incoming = frame([movie(name='Alien translated', rating=5, **{'Letterboxd URI': 'https://letterboxd.com/film/alien'})])
        added, _, retained = compute_dataset_diff(existing, incoming)
        self.assertTrue(added.empty)
        self.assertEqual(retained.iloc[0]['Rating'], 5)

    def test_full_watched_does_not_resurrect_deleted_diary_films(self):
        incoming = merge_letterboxd_dfs({'watched.csv': frame([movie()]),
                                        'diary.csv': frame([movie('Aliens', 1986)])})
        self.assertEqual(len(incoming), 1)

    def test_zip_and_individual_csv_produce_same_update(self):
        csv = b'Name,Year,Rating\nAlien,1979,5\n'
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as handle:
            handle.writestr('export/ratings.csv', csv)
        from_zip, info = load_uploaded_files([Upload('export.zip', archive.getvalue())])
        from_csv, _ = load_uploaded_files([Upload('ratings.csv', csv)])
        pd.testing.assert_frame_equal(from_zip, from_csv)
        self.assertEqual(info['sync_mode'], 'partial')

    def test_nested_diary_is_not_a_duplicate_account_diary(self):
        for prefix in ('', 'letterboxd-export/'):
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, 'w') as handle:
                handle.writestr(prefix + 'watched.csv', b'Name,Year\nAlien,1979\n')
                handle.writestr(prefix + 'diary.csv', b'Name,Year,Rating\nAlien,1979,5\n')
                handle.writestr(prefix + 'tv/diary.csv', b'Name,Year,Rating\nTelevision,2026,1\n')
            imported, info = load_uploaded_files([Upload('export.zip', archive.getvalue())])
            self.assertEqual(len(imported), 1)
            self.assertEqual(imported.iloc[0]['Name'], 'Alien')
            self.assertEqual(imported.iloc[0]['Rating'], 5)
            self.assertEqual(info['sync_mode'], 'full')

    def test_invalid_ratings_fail_instead_of_clearing(self):
        with self.assertRaises(ValueError):
            merge_letterboxd_dfs({'ratings.csv': frame([movie(rating='bad')])})

    def test_unsupported_csv_rejected(self):
        with self.assertRaises(ValueError):
            load_uploaded_files([Upload('watchlist.csv', b'Name,Year\nAlien,1979\n')])

    def test_rating_only_update_persists_without_tmdb_and_is_idempotent(self):
        incoming = merge_letterboxd_dfs({'ratings.csv': frame([movie(rating=5)])})
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory, patch('services.importer_service.fetch_movie_metadata') as fetch:
            path = str(Path(directory) / 'movies.parquet')
            updated, summary = apply_dataset_update(self.existing, incoming, '', parquet_path=path)
            saved = pd.read_parquet(path)
            self.assertEqual(saved.iloc[0]['Rating'], 5)
            self.assertEqual(summary['ratings_updated'], 1)
            self.assertNotIn('_rating_present', saved.columns)
            _, second = apply_dataset_update(updated, incoming, '', parquet_path=path)
            self.assertEqual(second['ratings_updated'], 0)
            fetch.assert_not_called()

    def test_new_film_saves_tmdb_ids_and_preserves_retained_metadata(self):
        incoming = merge_letterboxd_dfs({'diary.csv': frame([movie('New Film', 2026, 4)])})
        metadata = dict(tmdb_id=123, collection_id=456, genres=['Drama'])
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory, patch('services.importer_service.fetch_movie_metadata', return_value=metadata):
            path = str(Path(directory) / 'movies.parquet')
            updated, summary = apply_dataset_update(self.existing, incoming, 'test', parquet_path=path)
            self.assertEqual(len(pd.read_parquet(path)), 3)
            self.assertEqual(updated.iloc[-1]['tmdb_id'], 123)
            self.assertEqual(updated.iloc[-1]['collection_id'], 456)
            self.assertEqual(summary['added'], 1)

    def test_partial_ratings_file_overrides_old_diary_rating_absence(self):
        incoming = merge_letterboxd_dfs({'diary.csv': frame([movie(rating=5)]),
            'ratings.csv': pd.DataFrame(columns=['Name', 'Year', 'Rating'])})
        self.assertTrue(pd.isna(incoming.iloc[0]['Rating']))
        _, removed, retained = compute_dataset_diff(self.existing, incoming)
        self.assertTrue(removed.empty)
        self.assertTrue(pd.isna(retained.iloc[0]['Rating']))
        self.assertEqual(retained.iloc[1]['Rating'], 3)

    def test_failed_save_preserves_existing_file(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = str(Path(directory) / 'movies.parquet')
            save_dataset(self.existing, path)
            before = Path(path).read_bytes()
            with patch.object(pd.DataFrame, 'to_parquet', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    save_dataset(frame([movie(rating=1)]), path)
            self.assertEqual(before, Path(path).read_bytes())

    def test_empty_partial_upload_leaves_library_unchanged(self):
        incoming = merge_letterboxd_dfs({'ratings.csv': pd.DataFrame(columns=['Name', 'Year', 'Rating'])})
        _, removed, retained = compute_dataset_diff(self.existing, incoming)
        self.assertTrue(removed.empty)
        self.assertEqual(len(retained), 2)


if __name__ == '__main__':
    unittest.main()

