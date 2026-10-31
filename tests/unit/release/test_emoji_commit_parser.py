"""Optional emoji must not change version decisions or mutate commit messages."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from semantic_release.commit_parser.angular import AngularCommitParser

from scripts.emoji_commit_parser import EmojiAngularParser


@pytest.mark.parametrize("prefix", ["", "✨ ", "⚡️ ", "  🐛 "])
@pytest.mark.parametrize(
    "message",
    [
        "feat: add action",
        "fix(ui): fix layout",
        "feat!: replace API",
        "chore: tooling",
        "fix: adjust API\n\nBREAKING CHANGE: new interface",
    ],
)
def test_emoji_preserves_standard_parser_decision(prefix, message):
    commit = SimpleNamespace(message=prefix + message, parents=[], hexsha="a" * 40)
    plain = SimpleNamespace(message=message, parents=[], hexsha="a" * 40)
    expected = AngularCommitParser().parse(plain)
    actual = EmojiAngularParser().parse(commit)
    actual = actual if isinstance(actual, list) else [actual]
    expected = expected if isinstance(expected, list) else [expected]
    assert [(p.bump, p.type, p.scope) for p in actual] == [
        (p.bump, p.type, p.scope) for p in expected
    ]
    assert commit.message == prefix + message


def test_original_message_is_restored_when_delegate_raises():
    commit = SimpleNamespace(message="✨ feat: sample")
    with patch.object(AngularCommitParser, "parse", side_effect=RuntimeError("fixture failure")):
        with pytest.raises(RuntimeError, match="fixture failure"):
            EmojiAngularParser().parse(commit)
    assert commit.message == "✨ feat: sample"
