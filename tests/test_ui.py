import io
import json
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
            at.text_area[0].input("Una recensione dal diario.")
            next(b for b in at.button if 'Collezione' in b.label).click().run()
            self.assert_no_errors(at)
            save.assert_called_once()
            self.assertTrue(save.call_args.args[0].iloc[-1]['physical_copy'])
            self.assertEqual(save.call_args.args[0].iloc[-1]['Rating'], 4)
            self.assertEqual(save.call_args.args[0].iloc[-1]['Review'], 'Una recensione dal diario.')
            balloons.assert_not_called()

    def test_overview_opens_film_in_regular_details_panel(self):
        library = pd.concat([
            LIBRARY.assign(poster_path='/alien.jpg', Date='2020-01-01'),
            LIBRARY.assign(Name='Aliens', Year=1986, Date='2021-01-01', Review='My review'),
        ], ignore_index=True)
        at = self.app(library)
        self.assertTrue(any('class="recent-film" href="/personal_space?film=1"' in item.value for item in at.markdown))
        at.query_params['film'] = '1'
        at.switch_page('pages/personal_space.py').run()
        self.assert_no_errors(at)
        self.assertEqual(at.selectbox[1].value, 1)
        self.assertEqual(at.text_area[0].value, 'My review')
        table = at.dataframe[0].value
        self.assertEqual(table.iloc[0]['Title'], 'Aliens')
        self.assertNotIn('Details', table.columns)

    def test_search_select_and_save_personal_review(self):
        at = self.app()
        with patch('services.importer_service.save_dataset') as save:
            at.switch_page('pages/personal_space.py').run()
            at.text_input[0].input('Alien').run()
            at.selectbox[1].select(0).run()
            self.assert_no_errors(at)
            at.text_area[0].input('Una recensione personale.').run()
            next(b for b in at.button if b.label == 'Salva la scheda').click().run()
            self.assert_no_errors(at)
            self.assertEqual(save.call_args.args[0].iloc[0]['Review'], 'Una recensione personale.')
            self.assertTrue(any(item.value == 'Una recensione personale.' for item in at.text))

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

    def test_deep_statistics_tables_start_at_one(self):
        stats_library = pd.DataFrame([
            {
                'Name': 'Parasite',
                'Year': 2019,
                'Rating': 5.0,
                'tmdb_rating': 6.0,
                'genres': ['Drama', 'Thriller'],
                'directors': ['Martin Scorsese'],
                'actors': ['Actor A', 'Actor B'],
                'Date': '2024-01-10',
                'physical_copy': True,
            },
            {
                'Name': 'Crash',
                'Year': 2004,
                'Rating': 1.0,
                'tmdb_rating': 9.0,
                'genres': ['Drama', 'Crime'],
                'directors': ['Martin Scorsese'],
                'actors': ['Actor A', 'Actor B'],
                'Date': '2024-01-10',
                'physical_copy': False,
            },
            {
                'Name': 'Pulp Fiction',
                'Year': 1994,
                'Rating': 4.5,
                'tmdb_rating': 8.5,
                'genres': ['Crime', 'Thriller'],
                'directors': ['Quentin Tarantino'],
                'actors': ['Actor A', 'Actor C'],
                'Date': '2024-02-15',
                'physical_copy': True,
            },
        ])
        at = self.app(stats_library)
        at.switch_page('pages/more_statistics.py').run()
        self.assert_no_errors(at)
        visible_tables = [
            table for table in at.dataframe
            if not json.loads(table.proto.columns or '{}').get('_index', {}).get('hidden', False)
        ]
        self.assertEqual(len(visible_tables), 14)
        for table in visible_tables:
            self.assertGreater(len(table.value), 0)
            self.assertEqual(list(table.value.index), list(range(1, len(table.value) + 1)))

    def test_sagas_two_sections_visual_cards_and_highlights(self):
        sagas_library = pd.DataFrame([
            {
                'Name': 'Dune',
                'Year': 2021,
                'Rating': 4.0,
                'tmdb_rating': 7.8,
                'genres': ['Sci-Fi', 'Adventure'],
                'directors': ['Denis Villeneuve'],
                'actors': ['Timothée Chalamet'],
                'Date': '2024-01-10',
                'poster_path': '/dune1.jpg',
                'runtime': 155,
                'physical_copy': True,
            },
            {
                'Name': 'Dune: Part Two',
                'Year': 2024,
                'Rating': 5.0,
                'tmdb_rating': 8.2,
                'genres': ['Sci-Fi', 'Adventure'],
                'directors': ['Denis Villeneuve'],
                'actors': ['Timothée Chalamet'],
                'Date': '2024-03-01',
                'poster_path': '/dune2.jpg',
                'runtime': 166,
                'physical_copy': False,
            },
            {
                'Name': 'The Godfather',
                'Year': 1972,
                'Rating': 5.0,
                'tmdb_rating': 8.7,
                'genres': ['Crime', 'Drama'],
                'directors': ['Francis Ford Coppola'],
                'actors': ['Marlon Brando'],
                'Date': '2024-02-15',
                'poster_path': '/gf1.jpg',
                'runtime': 175,
                'physical_copy': True,
            },
        ])
        at = self.app(sagas_library)
        at.switch_page('pages/more_statistics.py').run()
        self.assert_no_errors(at)
        tab_labels = [tab.label for tab in at.tabs]
        self.assertTrue(any('Saghe completate (1)' in label for label in tab_labels))
        self.assertTrue(any('Saghe da completare (1)' in label for label in tab_labels))
        rendered_html = "\n".join(item.value for item in at.markdown)
        self.assertIn('https://image.tmdb.org/t/p/w342/dune1.jpg', rendered_html)
        self.assertIn('https://image.tmdb.org/t/p/w342/gf1.jpg', rendered_html)
        self.assertIn('Denis Villeneuve', rendered_html)
        self.assertIn('Francis Ford Coppola', rendered_html)
        self.assertIn('Dune: Part Two', rendered_html)
        self.assertIn('The Godfather Part II', rendered_html)
        self.assertNotIn('RoboCop', rendered_html)
        self.assertNotIn('Men in Black', rendered_html)
        self.assertNotIn('Before Trilogy', rendered_html)

    def test_ratings_normalized_to_10_scale_across_pages(self):
        from services.ui_components import _color_for_rating
        from services.importer_service import merge_letterboxd_dfs, compute_dataset_diff

        self.assertNotEqual(_color_for_rating(1.0), _color_for_rating(5.0))
        self.assertNotEqual(_color_for_rating(5.0), _color_for_rating(10.0))

        # 1. Overview (LIBRARY has Alien Rating=4.0 -> 8/10)
        at = self.app()
        self.assert_no_errors(at)
        self.assertEqual(at.metric[1].value, '8.00 / 10')
        ov_md = "\n".join(item.value for item in at.markdown)
        self.assertIn('8 / 10', ov_md)
        self.assertNotIn('/ 5', ov_md)

        # 2. Personal Movie Space (avg KPI, badge, table, 1-10 integer slider saving 9 -> 4.5)
        with patch('services.importer_service.save_dataset') as save:
            at = self.app()
            at.query_params['film'] = '0'
            at.switch_page('pages/personal_space.py').run()
            self.assert_no_errors(at)
            self.assertEqual(at.metric[3].value, '8.00 / 10 ★')
            self.assertEqual(at.dataframe[0].value.iloc[0]['Your Rating'], '8 / 10 ★')
            slider = at.select_slider[0]
            self.assertEqual(slider.options, ['Unrated'] + [f'{i} ★' for i in range(1, 11)])
            self.assertEqual(slider.value, '8 ★')
            slider.set_value('9 ★').run()
            next(b for b in at.button if b.label == 'Salva la scheda').click().run()
            self.assert_no_errors(at)
            self.assertEqual(save.call_args.args[0].iloc[0]['Rating'], 4.5)

        # 3. Add Movie (1-10 integer slider saving 7 -> 3.5)
        movie = dict(id=11, title='Ten Scale Test', year=2024, poster_url='https://image.tmdb.org/t/p/w300/test.jpg', tmdb_rating=7)
        details = dict(tmdb_id=11, title='Ten Scale Test', year=2024, genres=[], directors=[], actors=[], production_countries=[])
        at = self.app()
        at.session_state['search_results'] = [movie]
        with patch('services.tmbd_service.fetch_movie_details_by_id', return_value=details), patch('services.importer_service.save_dataset') as save:
            at.switch_page('pages/add_movie.py').run()
            at.button(key='movie_cover_11').click().run()
            slider = at.select_slider[0]
            self.assertEqual(slider.options, ['—'] + [f'{i} ★' for i in range(1, 11)])
            self.assertEqual(slider.value, 8)
            slider.set_value(7)
            next(b for b in at.button if 'Collezione' in b.label).click().run()
            self.assert_no_errors(at)
            self.assertEqual(save.call_args.args[0].iloc[-1]['Rating'], 3.5)

        # 4. Deep Statistics & Sagas (1-10 across KPI, tables, awards, sagas)
        stats_lib = pd.DataFrame([
            {
                'Name': 'Dune',
                'Year': 2021,
                'Rating': 4.0,
                'tmdb_rating': 7.8,
                'genres': ['Sci-Fi'],
                'directors': ['Denis Villeneuve'],
                'actors': ['Timothée Chalamet'],
                'Date': '2024-01-10',
                'poster_path': '/dune1.jpg',
                'physical_copy': True,
            },
            {
                'Name': 'Dune: Part Two',
                'Year': 2024,
                'Rating': 5.0,
                'tmdb_rating': 8.2,
                'genres': ['Sci-Fi'],
                'directors': ['Denis Villeneuve'],
                'actors': ['Timothée Chalamet'],
                'Date': '2024-03-01',
                'poster_path': '/dune2.jpg',
                'physical_copy': False,
            },
            {
                'Name': 'Parasite',
                'Year': 2019,
                'Rating': 4.5,
                'tmdb_rating': 8.5,
                'genres': ['Drama'],
                'directors': ['Bong Joon Ho'],
                'actors': ['Song Kang-ho'],
                'Date': '2024-02-01',
                'poster_path': '/para.jpg',
                'physical_copy': False,
            },
        ])
        at = self.app(stats_lib)
        at.switch_page('pages/more_statistics.py').run()
        self.assert_no_errors(at)
        self.assertEqual(at.metric[2].value, '9.00 / 10 ★')
        dir_table = at.dataframe[0].value
        self.assertIn('Tuo Voto (/10)', dir_table.columns)
        self.assertEqual(float(dir_table.iloc[0]['Tuo Voto (/10)']), 9.0)
        stats_md = "\n".join(item.value for item in at.markdown)
        self.assertIn('9.00 / 10', stats_md)
        self.assertNotRegex(stats_md, r'(\.\d+ / 5\b|/ 5 ★|/ 5 \()')

        # 5. Data Manager preview shows 1-10 scale
        existing_dm = pd.DataFrame([{'Name': 'Alien', 'Year': 1979, 'Rating': 4.0}])
        incoming_dm = merge_letterboxd_dfs({'ratings.csv': pd.DataFrame([{'Name': 'Alien', 'Year': 1979, 'Rating': 2.0}])})
        _, _, ret = compute_dataset_diff(existing_dm, incoming_dm)
        self.assertEqual(ret.attrs['rating_changes'][0]['Previous rating'], 4.0)
        at = self.app(existing_dm)
        with patch.object(st, 'file_uploader', return_value=[Upload('ratings.csv', b'Name,Year,Rating\nAlien,1979,2\n')]):
            at.switch_page('pages/data_manager.py').run()
        self.assert_no_errors(at)
        preview_df = at.dataframe[0].value
        self.assertIn('Voto precedente / 10', preview_df.columns)
        self.assertEqual(float(preview_df.iloc[0]['Voto precedente / 10']), 8.0)
        self.assertEqual(float(preview_df.iloc[0]['Voto attuale / 10']), 4.0)

    def test_completed_sagas_chart_trim_and_flop_toggle(self):
        from services.sagas_view import _select_completed_chart_sagas

        synthetic = [
            {'name': f'Saga {i:02d}', 'avg_user_rating': float(r), 'ratings_count': 2}
            for i, r in enumerate([9.5, 4.0, 8.0, 2.5, 10.0, 6.0, 7.5, 3.0, 8.5, 5.5, 9.0, 1.5], start=1)
        ]
        top_10 = _select_completed_chart_sagas(synthetic)
        self.assertEqual(len(top_10), 10)
        self.assertEqual([s['avg_user_rating'] for s in top_10[:3]], [10.0, 9.5, 9.0])

        top_4 = _select_completed_chart_sagas(synthetic, limit=4, show_flop=False)
        self.assertEqual([s['avg_user_rating'] for s in top_4], [10.0, 9.5, 9.0, 8.5])

        flop_4 = _select_completed_chart_sagas(synthetic, limit=4, show_flop=True)
        self.assertEqual([s['avg_user_rating'] for s in flop_4], [1.5, 2.5, 3.0, 4.0])

        sagas_lib = pd.DataFrame([
            {'Name': 'Dune', 'Year': 2021, 'Rating': 4.5, 'tmdb_rating': 7.8, 'genres': ['Sci-Fi'], 'directors': ['Denis Villeneuve'], 'actors': ['Timothée Chalamet'], 'Date': '2024-01-10', 'poster_path': '/dune1.jpg'},
            {'Name': 'Dune: Part Two', 'Year': 2024, 'Rating': 5.0, 'tmdb_rating': 8.2, 'genres': ['Sci-Fi'], 'directors': ['Denis Villeneuve'], 'actors': ['Timothée Chalamet'], 'Date': '2024-03-01', 'poster_path': '/dune2.jpg'},
            {'Name': 'Blade Runner', 'Year': 1982, 'Rating': 4.0, 'tmdb_rating': 7.9, 'genres': ['Sci-Fi'], 'directors': ['Ridley Scott'], 'actors': ['Harrison Ford'], 'Date': '2024-02-01', 'poster_path': '/br1.jpg'},
            {'Name': 'Blade Runner 2049', 'Year': 2017, 'Rating': 4.0, 'tmdb_rating': 7.6, 'genres': ['Sci-Fi'], 'directors': ['Denis Villeneuve'], 'actors': ['Ryan Gosling'], 'Date': '2024-02-02', 'poster_path': '/br2.jpg'},
            {'Name': 'Top Gun', 'Year': 1986, 'Rating': 2.0, 'tmdb_rating': 7.1, 'genres': ['Action'], 'directors': ['Tony Scott'], 'actors': ['Tom Cruise'], 'Date': '2024-02-05', 'poster_path': '/tg1.jpg'},
            {'Name': 'Top Gun: Maverick', 'Year': 2022, 'Rating': 3.0, 'tmdb_rating': 8.2, 'genres': ['Action'], 'directors': ['Joseph Kosinski'], 'actors': ['Tom Cruise'], 'Date': '2024-02-06', 'poster_path': '/tg2.jpg'},
        ])
        at = self.app(sagas_lib)
        at.switch_page('pages/more_statistics.py').run()
        self.assert_no_errors(at)
        self.assertEqual(at.number_input(key='sagas_completed_chart_limit').value, 10)
        md = "\n".join(item.value for item in at.markdown)
        self.assertIn('Top 3 saghe completate per voto medio', md)

        at.number_input(key='sagas_completed_chart_limit').set_value(2).run()
        self.assert_no_errors(at)
        md = "\n".join(item.value for item in at.markdown)
        self.assertIn('Top 2 saghe completate per voto medio · su 3 votate', md)

        at.button(key='sagas_completed_chart_flip').click().run()
        self.assert_no_errors(at)
        self.assertTrue(at.session_state['sagas_completed_chart_flop'])
        md = "\n".join(item.value for item in at.markdown)
        self.assertIn('Flop 2 saghe completate (voto medio più basso) · su 3 votate', md)
        self.assertIn('TOP', at.button(key='sagas_completed_chart_flip').label)

        at.button(key='sagas_completed_chart_flip').click().run()
        self.assert_no_errors(at)
        self.assertFalse(at.session_state['sagas_completed_chart_flop'])
        md = "\n".join(item.value for item in at.markdown)
        self.assertIn('Top 2 saghe completate per voto medio · su 3 votate', md)


if __name__ == '__main__':
    unittest.main()
