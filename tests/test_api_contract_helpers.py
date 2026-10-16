"""Regression checks for reusable endpoint contract assertions."""

import re
import unittest
from unittest.mock import Mock, patch

from jsonschema import Draft202012Validator, RefResolver, SchemaError, ValidationError

from .test_endpoints import checks


class TestContractHelpers(unittest.TestCase):
    def test_locale_boolean_is_not_treated_as_language_code(self):
        client = Mock()
        spec = {
            "paths": {
                "/api/events/": {
                    "get": {
                        "parameters": [
                            {
                                "name": "locale",
                                "in": "query",
                                "schema": {"type": "string"},
                            }
                        ]
                    }
                },
                "/api/types/default/": {
                    "get": {
                        "parameters": [
                            {
                                "name": "locale",
                                "in": "query",
                                "schema": {"type": "boolean"},
                            }
                        ]
                    }
                },
                "/api/bookmarks/": {"get": {"parameters": []}},
            }
        }
        with patch.object(checks, "_get_openapi_spec", return_value=(spec, None)):
            self.assertEqual(
                checks._fixture_locale_url(client, "/api/events/", "en"),
                "/api/events/?locale=en",
            )
            for url in (
                "/api/types/default/",
                "/api/bookmarks/",
                "/api/events/?locale=de",
                "/api/types/default/?locale=true",
            ):
                self.assertEqual(checks._fixture_locale_url(client, url, "en"), url)
            self.assertEqual(
                checks._fixture_locale_url(client, "/api/events/", None), "/api/events/"
            )

    def test_schema_is_checked_once_and_every_result_is_validated(self):
        schema = {
            "type": "object",
            "required": ["id"],
            "properties": {"id": {"type": "integer"}},
        }
        resolver = RefResolver("", schema)
        with patch.object(
            Draft202012Validator,
            "check_schema",
            wraps=Draft202012Validator.check_schema,
        ) as checked:
            checks._validate_schema_results(
                [{"id": 1}, {"id": 2}, {"id": 3}], schema, resolver
            )
        self.assertEqual(checked.call_count, 1)
        with self.assertRaises(ValidationError):
            checks._validate_schema_results(
                [{"id": 1}, {"id": "invalid second row"}], schema, resolver
            )
        with self.assertRaises(SchemaError):
            checks._validate_schema_results([], {"type": "invalid-schema"}, resolver)

    def test_sort_helper_matches_english_raw_type_values(self):
        client = Mock()
        client.get.return_value.status_code = 200
        client.get.return_value.json = [{"type": "Birth"}, {"type": "Burial"}]
        self.client = client
        with (
            patch.object(checks, "fetch_header", return_value={}),
            patch.object(
                checks, "_localizable_paths", return_value=(re.compile("/api/events/"),)
            ),
        ):
            checks.check_sort_parameter(self, "/api/events/", "type")
        url = client.get.call_args.args[0]
        self.assertIn("locale=en", url)
        self.assertIn("keys=type&sort=+type", url)
