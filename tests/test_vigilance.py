import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from meteole._vigilance import Vigilance


class TestVigilance(unittest.TestCase):
    def setUp(self):
        self.api_key = "fake_api_key"
        self.token = "fake_token"
        self.application_id = "fake_app_id"
        self.vigilance = Vigilance(api_key=self.api_key, token=self.token, application_id=self.application_id)

    @patch("meteole._vigilance.Vigilance._get_request")
    def test_get_vigilance_bulletin(self, mock_get_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "some_data"}
        mock_get_request.return_value = mock_response

        result = self.vigilance.get_vigilance_bulletin()
        self.assertEqual(result, {"data": "some_data"})
        mock_get_request.assert_called_once_with(
            "https://public-api.meteofrance.fr/public/DPVigilance/v1/textesvigilance/encours"
        )

    @patch("meteole._vigilance.Vigilance._get_request")
    def test_get_vigilance_map(self, mock_get_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "some_data"}
        mock_get_request.return_value = mock_response

        result = self.vigilance.get_vigilance_map()
        self.assertEqual(result, {"data": "some_data"})
        mock_get_request.assert_called_once_with(
            "https://public-api.meteofrance.fr/public/DPVigilance/v1/cartevigilance/encours"
        )

    @patch("meteole._vigilance.Vigilance.get_vigilance_map")
    def test_get_phenomenon(self, mock_get_vigilance_map):
        mock_get_vigilance_map.return_value = {
            "product": {
                "periods": [
                    {
                        "echeance": "J",
                        "per_phenomenon_items": [
                            {
                                "phenomenon_id": "1",
                                "any_color_count": 5,
                                "phenomenon_counts": [{"color_id": 2, "color_name": "Jaune", "count": 3}],
                            }
                        ],
                        "timelaps.domain_ids": [{"domain_id": 1, "max_color_id": 1}],
                    },
                    {
                        "echeance": "J1",
                        "per_phenomenon_items": [
                            {
                                "phenomenon_id": "2",
                                "any_color_count": 5,
                                "phenomenon_counts": [{"color_id": 2, "color_name": "Jaune", "count": 3}],
                            }
                        ],
                        "timelaps.domain_ids": [{"domain_id": 2, "max_color_id": 2}],
                    },
                ]
            }
        }

        with patch.object(self.vigilance, "get_vigilance_map", return_value=mock_get_vigilance_map.return_value):
            df_phenomenon, df_timelaps = self.vigilance.get_phenomenon()

            expected_phenomenon_data = {
                "phenomenon_id": ["1", "2"],
                "any_color_count": [5, 5],
                "phenomenon_counts": [
                    [{"color_id": 2, "color_name": "Jaune", "count": 3}],
                    [{"color_id": 2, "color_name": "Jaune", "count": 3}],
                ],
                "echeance": ["J", "J1"],
                "phenomenon_libelle": ["wind", "rain"],
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
