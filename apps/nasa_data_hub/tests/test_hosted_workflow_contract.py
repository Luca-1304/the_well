from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "nasa-data-hub.yml"


class HostedWorkflowContractTests(unittest.TestCase):
    def test_deployable_hosted_app_is_verified_on_node_22(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        for marker in (
            "  hosted:",
            "name: Hosted app — Node 22",
            "working-directory: apps/nasa_data_hub/hosted",
            "uses: actions/setup-node@v6",
            'node-version: "22"',
            "run: npm run check",
        ):
            self.assertIn(marker, workflow)

    def test_every_checkout_discards_authentication_after_clone(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        checkout_count = workflow.count("uses: actions/checkout@")

        self.assertGreaterEqual(checkout_count, 2)
        self.assertEqual(
            workflow.count("persist-credentials: false"),
            checkout_count,
        )

    def test_pull_requests_do_not_compare_against_current_production(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertNotIn("npm run smoke:production", workflow)
        self.assertNotIn("nasa-data-hub.vercel.app", workflow)


if __name__ == "__main__":
    unittest.main()
