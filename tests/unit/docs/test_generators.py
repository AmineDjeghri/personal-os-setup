"""Run the actual documentation generators against isolated source trees."""

from pathlib import Path
import runpy

import mkdocs_gen_files
import pytest

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def generated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "generated"

    def open_output(path, mode):
        destination = output / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination.open(mode, encoding="utf-8")

    monkeypatch.setitem(mkdocs_gen_files.__dict__, "open", open_output)
    return tmp_path, output


def test_api_generation_skips_payload_and_only_exact_init_files(generated):
    root, output = generated
    package = root / "src/personal_os_setup"
    (package / "config/third-party").mkdir(parents=True)
    for name in ("__init__.py", "api.py", "my__init__helper.py", "config/third-party/payload.py"):
        (package / name).write_text("")
    runpy.run_path(str(REPO / "scripts/gen_doc_stubs.py"))
    assert (
        output / "package/personal_os_setup/api.md"
    ).read_text() == "::: personal_os_setup.api\n"
    assert (output / "package/personal_os_setup/my__init__helper.md").is_file()
    assert not (output / "package/personal_os_setup/__init__.md").exists()
    assert not (output / "package/personal_os_setup/config").exists()
    summary = (output / "package/SUMMARY.md").read_text()
    assert "personal_os_setup/api.md" in summary
    assert "payload" not in summary


def test_example_generation_preserves_nested_paths_code_and_table_columns(generated):
    root, output = generated
    examples = root / "docs/examples/nested"
    examples.mkdir(parents=True)
    (examples / "hello_world.py").write_text('"""Use A | B.\n\nMore details."""\nprint("hello")\n')
    (examples / "__init__.py").write_text("")
    runpy.run_path(str(REPO / "scripts/gen_example_pages.py"))
    page = (output / "docs/examples/nested/hello_world.md").read_text()
    assert '```python\n"""Use A | B.' in page
    index = (output / "docs/examples/index.md").read_text()
    assert r"[Hello World](nested/hello_world.md) | Use A \| B" in index
    assert "__init__" not in index
    assert "nested/hello_world.md" in (output / "docs/examples/SUMMARY.md").read_text()
