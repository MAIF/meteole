import unittest
from unittest.mock import patch, MagicMock
from meteole.vigilance import Vigilance
import pandas as pd

class TestVigilance(unittest.TestCase):

    def setUp(self):
        self.api_key = "fake_api_key"
        self.token = "fake_token"
        self.application_id = "fake_app_id"
        self.vigilance = Vigilance(api_key=self.api_key, token=self.token, application_id=self.application_id)

    @patch("meteole.vigilance.Vigilance._get_request")
    def test_get_textes_vigilance(self, mock_get_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "some_data"}
        mock_get_request.return_value = mock_response

        result = self.vigilance.get_textes_vigilance()
        self.assertEqual(result, {"data": "some_data"})
        mock_get_request.assert_called_once_with("https://public-api.meteofrance.fr/public/DPVigilance/v1/textesvigilance/encours")

    @patch("meteole.vigilance.Vigilance._get_request")
    def test_get_carte_vigilance(self, mock_get_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "some_data"}
        mock_get_request.return_value = mock_response

        result = self.vigilance.get_carte_vigilance()
        self.assertEqual(result, {"data": "some_data"})
        mock_get_request.assert_called_once_with("https://public-api.meteofrance.fr/public/DPVigilance/v1/cartevigilance/encours")

    @patch("meteole.vigilance.Vigilance.get_carte_vigilance")
    def test_get_phenomenon(self, mock_get_carte_vigilance):
        mock_get_carte_vigilance.return_value = {
            "product": {
                    "periods": [
                        {"echeance": "J",
                         "per_phenomenon_items": [{"phenomenon_id": '1', "any_color_count": 5, "phenomenon_counts": [{"color_id": 2, "color_name": "Jaune", "count": 3}]}],
                         "timelaps.domain_ids": [{"domain_id": 1, 'max_color_id': 1}]},
                        {"echeance": "J1",
                         "per_phenomenon_items": [{"phenomenon_id": '2', "any_color_count": 5, "phenomenon_counts": [{"color_id": 2, "color_name": "Jaune", "count": 3}]}],
                         "timelaps.domain_ids": [{"domain_id": 2, 'max_color_id': 2}]}
                    ]
                }
        }

        with patch.object(self.vigilance, 'get_carte_vigilance', return_value=mock_get_carte_vigilance.return_value):
            df_phenomenon, df_timelaps = self.vigilance.get_phenomenon()

            expected_phenomenon_data = {
                "phenomenon_id": ['1', '2'],
                "any_color_count": [5, 5],
                "phenomenon_counts": [[{"color_id": 2, "color_name": "Jaune", "count": 3}], [{"color_id": 2, "color_name": "Jaune", "count": 3}]],
                "echeance": ["J", "J1"],
                "phenomenon_libelle": ["vent", "pluie"]
            }
            expected_phenomenon_df = pd.DataFrame(expected_phenomenon_data)

            expected_timelaps_data = {
                "domain_id": [1, 2],
                "max_color_id": [1, 2],
                "echeance": ["J", "J1"],
            }
            expected_timelaps_df = pd.DataFrame(expected_timelaps_data)

            pd.testing.assert_frame_equal(df_phenomenon, expected_phenomenon_df)
            pd.testing.assert_frame_equal(df_timelaps, expected_timelaps_df)