from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "fifteen-pass-verification.yml"


class FifteenPassDiagnosticContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_parent_suite_records_each_pass_separately(self) -> None:
        self.assertIn("diagnostics/parent-pass-${pass_number}.log", self.workflow)
        self.assertIn("PARENT PASS ${pass_number}/15", self.workflow)
        self.assertIn("PIPESTATUS[0]", self.workflow)

    def test_parent_suite_records_environment_parameters(self) -> None:
        for parameter in (
            "PYTHONHASHSEED",
            "TZ",
            "LC_ALL",
            "python --version",
            "uv --version",
        ):
            with self.subTest(parameter=parameter):
                self.assertIn(parameter, self.workflow)

    def test_diagnostics_are_uploaded_even_when_a_pass_fails(self) -> None:
        self.assertIn("uses: actions/upload-artifact@v7", self.workflow)
        self.assertIn("if: always()", self.workflow)
        self.assertIn("path: diagnostics/", self.workflow)


if __name__ == "__main__":
    unittest.main()
