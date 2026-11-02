import io
import unittest
from unittest.mock import patch
import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest
from test_importer import Upload


LIBRARY = pd.DataFrame([{'Name': 'Alien', 'Year': 1979, 'Rating': 4.0,
    'tmdb_rating': 8.0, 'genres': ['Horror'], 'directors': ['Ridley Scott'], 'physical_copy': True}])


class InterfaceTests(unittest.TestCase):
    def app(self, data=LIBRARY):
        at = AppTest.from_file('app.py', default_timeout=30)
        at.session_state['enriched_data'] = data.copy()
        at.session_state['data_loaded'] = True
        at.session_state['lang'] = 'it'
        return at.run()

    def assert_no_errors(self, at):
        self.assertEqual([e.message for e in at.exception], [])

    def test_navigation_and_saga_filters(self):
        at = self.app()
        self.assert_no_errors(at)
        self.assertEqual(len(at.get('file_uploader')), 0)
        for page in ('pages/data_manager.py', 'pages/more_statistics.py', 'pages/settings.py'):
            at = self.app()
            at.switch_page(page).run()
            self.assert_no_errors(at)
            if page == 'pages/more_statistics.py':
                self.assertTrue(any('Saghe' in tab.label for tab in at.tabs))

    def test_cover_opens_dialog_and_saves_without_balloons(self):
        at = self.app()
        movie = dict(id=10, title='Test Movie', year=2024, poster_url='https://image.tmdb.org/t/p/w300/test.jpg', tmdb_rating=7)
        details = dict(tmdb_id=10, title='Test Movie', year=2024, genres=[], directors=[], actors=[], production_countries=[])
        at.session_state['search_results'] = [movie]
        with patch('services.tmbd_service.fetch_movie_details_by_id', return_value=details), patch('services.importer_service.save_dataset') as save, patch.object(st, 'balloons') as balloons:
            at.switch_page('pages/add_movie.py').run()
            self.assert_no_errors(at)
            at.button(key='movie_cover_10').click().run()
            self.assert_no_errors(at)
            self.assertTrue(at.get('dialog'))
            at.checkbox[0].check()
            next(b for b in at.button if 'Collezione' in b.label).click().run()
            self.assert_no_errors(at)
            save.assert_called_once()
            self.assertTrue(save.call_args.args[0].iloc[-1]['physical_copy'])
            self.assertEqual(save.call_args.args[0].iloc[-1]['Rating'], 4)
            balloons.assert_not_called()

    def test_initial_import_preview_does_not_use_dataframe_truthiness(self):
        at = self.app(pd.DataFrame())
        with patch.object(st, 'file_uploader', return_value=[Upload('ratings.csv', b'Name,Year,Rating\nAlien,1979,5\n')]):
            at.switch_page('pages/data_manager.py').run()
        self.assert_no_errors(at)
        self.assertEqual(at.metric[0].value, '1')

    def test_rating_preview_and_save_use_same_update(self):
        at = self.app()
        upload = Upload('ratings.csv', b'Name,Year,Rating\nAlien,1979,2\n')
        with patch.object(st, 'file_uploader', return_value=[upload]), patch('services.importer_service.save_dataset') as save:
            at.switch_page('pages/data_manager.py').run()
            self.assert_no_errors(at)
            self.assertEqual(at.metric[3].value, '1')
            button = next(b for b in at.button if 'Sincronizza' in b.label)
            button.click().run()
            self.assert_no_errors(at)
            self.assertEqual(save.call_count, 1)
            self.assertEqual(save.call_args.args[0].iloc[0]['Rating'], 2)
            self.assertEqual(at.session_state['enriched_data'].iloc[0]['Rating'], 2)


if __name__ == '__main__':
    unittest.main()
