"""Production code must not depend on evaluation or ground truth."""

import ast
from pathlib import Path


def test_src_never_imports_eval_or_reads_ground_truth() -> None:
    source_root = Path(__file__).resolve().parents[2] / "src/unmess"
    for path in source_root.rglob("*.py"):
        source = path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(not alias.name.startswith("eval") for alias in node.names), path
            elif isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("eval"), path
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert "ground_truth" not in node.value, path
