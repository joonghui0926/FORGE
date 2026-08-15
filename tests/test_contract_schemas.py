from __future__ import annotations

import json
from pathlib import Path
import unittest


class ContractSchemaTest(unittest.TestCase):
    def test_contract_schemas_are_parseable_and_version_unique(self) -> None:
        root = Path("packages/contracts/schemas")
        documents = [json.loads(path.read_text(encoding="utf-8")) for path in root.glob("*.json")]
        self.assertGreaterEqual(len(documents), 4)
        titles = [document["title"] for document in documents]
        self.assertEqual(len(titles), len(set(titles)))
        self.assertTrue(all(document.get("$schema") for document in documents))


if __name__ == "__main__":
    unittest.main()
