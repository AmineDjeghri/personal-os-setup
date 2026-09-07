"""This script walks through the source code and generates a markdown file for each python file.

The goal is then for the markdown files to be used by mkdocs to call the plugin mkdocstring.
"""

from pathlib import Path

import mkdocs_gen_files

src_root = Path("src")
config_root = src_root / "personal_os_setup" / "config"
nav = mkdocs_gen_files.Nav()

for path in sorted(src_root.glob("**/*.py")):
    if "__init__" in str(path):
        print("Skipping", path)
        continue
    # Only the importable package is API.
    if config_root in path.parents:
        print("Skipping", path)
        continue
    doc_path = Path("package", path.relative_to(src_root)).with_suffix(".md")

    with mkdocs_gen_files.open(doc_path, "w") as f:
        ident = ".".join(path.relative_to(src_root).with_suffix("").parts)
        print("::: " + ident, file=f)
    nav[path.relative_to(src_root).with_suffix("").parts] = (
        path.relative_to(src_root).with_suffix(".md").as_posix()
    )

with mkdocs_gen_files.open("package/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
