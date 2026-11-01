"""Generate Markdown documentation pages for example Python scripts."""

import ast
from pathlib import Path

import mkdocs_gen_files

examples_root = Path("docs/examples")

index_rows: list[str] = []
summary_lines = ["* [Overview](index.md)\n"]

for path in sorted(
    p for p in examples_root.rglob("*.py") if p.stem != "__init__" and "__pycache__" not in p.parts
):
    source = path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(source)
        docstring = ast.get_docstring(tree) or ""
    except SyntaxError:
        docstring = ""

    title = path.stem.replace("_", " ").title()
    first_line = docstring.split("\n")[0].rstrip(".") if docstring else ""

    first_line = first_line.replace("|", "\\|")

    # Preserve subfolder structure relative to examples_root
    rel_path = path.relative_to(examples_root)
    doc_rel = rel_path.with_suffix(".md").as_posix()

    # Use subfolder prefix in index and summary (e.g. "scripts/run_evaluation_example")
    index_rows.append(f"| [{title}]({doc_rel}) | {first_line} |")
    summary_lines.append(f"* [{title}]({doc_rel})\n")

    lines = [f"# {title}", ""]
    if docstring:
        lines += [docstring, ""]
    lines += [
        "```python",
        source.rstrip(),
        "```",
        "",
    ]

    doc_path = Path("docs/examples") / doc_rel
    with mkdocs_gen_files.open(doc_path, "w") as f:
        f.write("\n".join(lines))

index_lines = [
    "# Examples",
    "",
    "Ready-to-run code examples covering common use cases.",
    "",
    "| Example | Description |",
    "| --- | --- |",
    *index_rows,
    "",
]

with mkdocs_gen_files.open("docs/examples/index.md", "w") as f:
    f.write("\n".join(index_lines))

with mkdocs_gen_files.open("docs/examples/SUMMARY.md", "w") as f:
    f.writelines(summary_lines)
