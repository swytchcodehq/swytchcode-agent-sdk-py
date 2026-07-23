import unittest
from swytchcode_runtime.client import Swytchcode, _make_alias
from unittest.mock import patch


class TestAlias(unittest.TestCase):
    @patch("swytchcode_runtime.discover.info")
    @patch("swytchcode_runtime.discover.search")
    def test_deterministic_alias(self, mock_search, mock_info):
        long_id = "google_workspace_admin_directory_users_aliases_insert_extra_padding_to_exceed_limit"
        mock_search.return_value = [{"canonical_id": long_id}]
        mock_info.return_value = {
            "inputs": {"email": {"TYPE": "STRING"}},
            "summary": "Test tool",
        }

        client = Swytchcode()
        tools = client.tools.get(search="test")
        self.assertEqual(len(tools), 1)
        alias = tools[0].name

        self.assertLessEqual(len(alias), 64)

        # Test determinism
        client2 = Swytchcode()
        tools2 = client2.tools.get(search="test")
        self.assertEqual(tools2[0].name, alias)

        # Test collision
        taken = {}
        alias1 = _make_alias("a.b", taken)
        taken[alias1] = "a.b"
        alias2 = _make_alias("a_b", taken)  # Collides on sanitize

        self.assertNotEqual(alias1, alias2)
        
        import re
        self.assertTrue(re.search(r"_[0-9a-f]{6}$", alias2) or re.search(r"_[0-9a-f]{6}$", alias1))


if __name__ == "__main__":
    unittest.main()
