import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from nasa_data_hub.cli import build_parser, main


class CLITests(unittest.TestCase):
    def test_health_requires_no_network_or_personal_key(self):
        output = io.StringIO()
        with patch.dict("os.environ", {}, clear=True), redirect_stdout(output):
            code = main(["--env-file", "/missing", "health"])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["using_demo_key"])

    def test_parser_understands_apod_date(self):
        args = build_parser().parse_args(["apod", "--date", "2026-08-02"])
        self.assertEqual(args.command, "apod")
        self.assertEqual(args.date.isoformat(), "2026-08-02")


if __name__ == "__main__":
    unittest.main()
