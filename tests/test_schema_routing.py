import unittest
from swytchcode_runtime.schema import simplify


class TestSchemaRouting(unittest.TestCase):
    def test_path_params_required(self):
        raw_schema = [
            {"userId": {"TYPE": "STRING", "LOCATION": "path", "DESC": "The user ID"}},
            {"amount": {"TYPE": "INT", "LOCATION": "query"}},
        ]

        simplified = simplify(raw_schema)

        # Path parameters should be required
        self.assertIn("userId", simplified["required"])
        self.assertEqual(simplified["properties"]["userId"]["type"], "string")
        self.assertEqual(simplified["properties"]["amount"]["type"], "integer")

    def test_json_schema_path_params_required(self):
        raw_schema = {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "location": "path"},
                "repo": {"type": "string", "location": "path"},
                "title": {"type": "string", "location": "body"},
            },
        }
        simplified = simplify(raw_schema)
        self.assertIn("owner", simplified["required"])
        self.assertIn("repo", simplified["required"])
        self.assertNotIn("title", simplified["required"])

    def test_split_by_location_json_schema(self):
        from swytchcode_runtime.client import _split_by_location

        raw_schema = {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "location": "path"},
                "title": {"type": "string", "location": "body"},
            },
        }
        args = {"owner": "swytchcode", "title": "hello"}
        result = _split_by_location(raw_schema, args)
        self.assertEqual(result.get("params", {}).get("owner"), "swytchcode")
        self.assertEqual(result.get("body", {}).get("title"), "hello")

    def test_split_by_location_array_wreken_shape(self):
        from swytchcode_runtime.client import _split_by_location

        raw_schema = [
            {"owner": {"TYPE": "STRING", "LOCATION": "path"}},
            {"title": {"TYPE": "STRING", "LOCATION": "body"}},
        ]
        args = {"owner": "swytchcode", "title": "hello"}
        result = _split_by_location(raw_schema, args)
        self.assertEqual(result.get("params", {}).get("owner"), "swytchcode")
        self.assertEqual(result.get("body", {}).get("title"), "hello")


if __name__ == "__main__":
    unittest.main()
