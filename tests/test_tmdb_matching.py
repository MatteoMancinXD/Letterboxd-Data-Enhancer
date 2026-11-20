import unittest
from unittest.mock import Mock, patch

from services.tmbd_service import fetch_movie_metadata


class TMDbMatchingTests(unittest.TestCase):
    @patch('services.tmbd_service.fetch_movie_details_by_id')
    @patch('services.tmbd_service.requests.get')
    def test_checks_title_and_year_before_fetching_credits(self, get, details):
        wrong_title = {'id': 752, 'title': 'V for Vendetta', 'release_date': '2022-01-01'}
        wrong_year = {'id': 225747, 'title': 'Vendetta', 'release_date': '2013-11-08'}
        correct = {'id': 894169, 'title': 'Vendetta', 'release_date': '2022-05-17'}
        response = Mock(status_code=200)
        response.json.return_value = {'results': [wrong_title, wrong_year, correct]}
        get.return_value = response
        details.return_value = {'year': 2022, 'directors': ['Jared Cohn']}
        self.assertEqual(fetch_movie_metadata('Vendetta', 2022.0, 'test'), details.return_value)
        details.assert_called_once_with(894169, 'test')

        details.reset_mock()
        response.json.return_value['results'].append({**correct, 'id': 1122079})
        self.assertIsNone(fetch_movie_metadata('Vendetta', 2022, 'test'))
        details.assert_not_called()


if __name__ == '__main__':
    unittest.main()
