"""Guard the shipped AIOStreams templates and the guide pages that document them."""

import json
from pathlib import Path
import re

import pytest

ANDROID_TV = Path(__file__).resolve().parents[3] / "docs" / "android-tv"
TEMPLATES = ["aiostreams-template-full.json", "aiostreams-template-essentials.json"]
PLACEHOLDER = "<optional_template_placeholder>"
PUBLIC_MANIFESTS = {"https://v3-cinemeta.strem.io/manifest.json"}
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
VARIANT_NAME = re.compile(r'presets\[options\.name="([^"]+)"\]')


def load(name: str) -> dict:
    return json.loads((ANDROID_TV / name).read_text(encoding="utf-8"))


def guide_pages() -> list[Path]:
    return sorted(ANDROID_TV.glob("*aiostreams*.md"))


@pytest.mark.parametrize("name", TEMPLATES)
def test_metadata_points_to_the_file_in_this_repo(name):
    metadata = load(name)["metadata"]
    assert metadata["sourceUrl"].endswith(f"/main/docs/android-tv/{name}")
    assert re.fullmatch(r"\d+\.\d+\.\d+", metadata["version"])


def test_both_templates_share_one_version():
    versions = {load(name)["metadata"]["version"] for name in TEMPLATES}
    assert len(versions) == 1


@pytest.mark.parametrize("name", TEMPLATES)
def test_custom_addons_ship_with_placeholder_urls(name):
    presets = load(name)["config"]["presets"]
    custom = [p for p in presets if p["type"] == "custom"]
    assert custom
    for preset in custom:
        url = preset["options"]["manifestUrl"]
        assert url == PLACEHOLDER or url in PUBLIC_MANIFESTS, preset["options"]["name"]


@pytest.mark.parametrize("name", TEMPLATES)
def test_templates_and_guide_hold_no_uuid_or_token(name):
    text = (ANDROID_TV / name).read_text(encoding="utf-8")
    assert not UUID.search(text)
    assert "eyJ" not in text
    for page in guide_pages():
        page_text = page.read_text(encoding="utf-8")
        assert not UUID.search(page_text), page.name
        assert "eyJ" not in page_text, page.name


@pytest.mark.parametrize("name", TEMPLATES)
def test_instance_ids_are_unique(name):
    ids = [p["instanceId"] for p in load(name)["config"]["presets"]]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("name", TEMPLATES)
def test_catalog_settings_name_existing_addons(name):
    config = load(name)["config"]
    addons = {p["options"]["name"] for p in config["presets"]}
    for catalog in config["catalogModifications"]:
        addon = catalog.get("addonName")
        assert addon is None or addon in addons, (catalog["id"], addon)
    catalog_ids = {c["id"] for c in config["catalogModifications"]}
    for merged in config["mergedCatalogs"]:
        assert merged["id"] in catalog_ids


@pytest.mark.parametrize("name", TEMPLATES)
def test_seeder_minimum_only_applies_to_torrents(name):
    config = load(name)["config"]
    if config["requiredSeederRange"][0] > 0:
        # an empty list means every stream type, and streams without seeder data count as 0
        assert config["seederRangeTypes"]
        assert set(config["seederRangeTypes"]) <= {"p2p", "uncached"}


def test_essentials_has_no_personal_addon():
    custom = [
        p["options"]["name"]
        for p in load(TEMPLATES[1])["config"]["presets"]
        if p["type"] == "custom"
    ]
    assert custom == ["Cinemeta"]


def test_variant_scripts_in_the_guide_match_template_addon_names():
    # `=` is exact and case-sensitive, so a typo silently disables nothing
    addons = {p["options"]["name"] for p in load(TEMPLATES[0])["config"]["presets"]}
    used = {
        name
        for page in guide_pages()
        for name in VARIANT_NAME.findall(page.read_text(encoding="utf-8"))
    }
    assert used
    assert used <= addons, used - addons
