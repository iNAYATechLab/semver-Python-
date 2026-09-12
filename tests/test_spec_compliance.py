"""
Regression tests for the defects found during the code audit.

Each test here fails against the original implementation. They cover
SemVer 2.0.0 compliance (pre-releases, build metadata, validation) and the
API robustness issues reported in the audit.
"""

import os

import pytest

import semver

from semver import EmptyConstraint
from semver import Version
from semver import VersionRange
from semver import VersionUnion
from semver import parse_constraint
from semver.exceptions import ParseVersionError


@pytest.mark.parametrize(
    "text,prerelease",
    [
        ("1.0.0-rc.1", ["rc", 1]),
        ("1.0.0-rc.1.2", ["rc", 1, 2]),
        ("1.0.0-alpha.1.2", ["alpha", 1, 2]),
        ("1.0.0-1.2.3", [1, 2, 3]),
        ("1.0.0-alpha.beta", ["alpha", "beta"]),
        ("1.0.0-foo", ["foo"]),
        ("1.0.0-x.7.z.92", ["x", 7, "z", 92]),
    ],
)
def test_prerelease_identifiers_are_kept(text, prerelease):
    """Pre-releases used to be dropped, turning them into stable releases."""
    version = Version.parse(text)

    assert version.prerelease == prerelease
    assert version.is_prerelease()
    assert version.build == []
    assert not version.is_prerelease() is False


@pytest.mark.parametrize(
    "text,post,build",
    [
        ("1.0.0-1", 1, []),
        ("1.0.0-post", None, []),
        ("1.0.0-post1", 1, []),
        ("1.0.0+post1", 1, []),
        ("1.0.0-post1+build", 1, ["build"]),
    ],
)
def test_post_release_convention_is_preserved(text, post, build):
    """A lone integer or a "post" marker after the release is a post-release."""
    version = Version.parse(text)

    assert version.post == post
    assert version.build == build
    assert not version.is_prerelease()


def test_post_releases_sort_above_the_release():
    """A post-release is greater than its release but lower than the next one."""
    release = Version.parse("1.0.0")
    post = Version.parse("1.0.0-post1")
    next_patch = Version.parse("1.0.1")

    assert post > release
    assert post < next_patch
    assert post != release
    assert max([release, post]) == post
    assert sorted([next_patch, release, post]) == [release, post, next_patch]

    assert parse_constraint(">1.0.0").allows(post)
    assert parse_constraint("<1.0.1").allows(post)
    assert not parse_constraint("<1.0.0").allows(post)
    assert Version.parse("1.0.0-post2") > Version.parse("1.0.0-post1")


def test_prerelease_is_lower_than_the_release():
    assert Version.parse("1.0.0-foo") < Version.parse("1.0.0")
    assert Version.parse("1.0.0-1.2.3") < Version.parse("1.0.0")
    assert Version.parse("1.0.0-rc.1.2") < Version.parse("1.0.0")
    assert Version.parse("1.0.0-x.7.z.92") < Version.parse("1.0.0")
    assert Version.parse("1.0.0-alpha.1.2") < Version.parse("1.0.0-alpha.2")


def test_spec_precedence_chain():
    """The ordering example from SemVer 2.0.0 s11."""
    versions = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]

    parsed = [Version.parse(version) for version in versions]

    assert [str(version) for version in sorted(parsed)] == versions
    assert max(parsed) == Version.parse("1.0.0")


def test_build_metadata_is_ignored_in_precedence():
    """Build metadata MUST be ignored when determining precedence (s10)."""
    assert Version.parse("1.0.0+a") == Version.parse("1.0.0+b")
    assert Version.parse("1.0.0+build") == Version.parse("1.0.0")
    assert not Version.parse("1.0.0+a") < Version.parse("1.0.0+b")
    assert not Version.parse("1.0.0+a") > Version.parse("1.0.0+b")
    assert Version.parse("1.0.0-rc.1+build.1") == Version.parse("1.0.0-rc.1")
    assert Version.parse("1.0.0-rc.1+build.1") < Version.parse("1.0.0")


def test_build_metadata_is_still_exposed():
    version = Version.parse("1.0.0-rc.1+build.1")

    assert version.build == ["build", 1]
    assert version.text == "1.0.0-rc.1+build.1"
    assert str(version) == "1.0.0-rc.1+build.1"


def test_build_metadata_constraints():
    assert parse_constraint(">1.0.0+b").allows(Version.parse("1.0.0")) is False
    assert parse_constraint(">=1.0.0+b").allows(Version.parse("1.0.0"))
    assert parse_constraint(">=1.0.0+b").allows(Version.parse("1.0.0+a"))
    assert parse_constraint("<=1.0.0+a").allows(Version.parse("1.0.0+b"))
    assert parse_constraint("1.0.0+b").allows(Version.parse("1.0.0+a"))


@pytest.mark.parametrize(
    "text,build",
    [
        ("1.0.0+postsponsor", ["sponsor"]),
        ("1.0.0+postoffice", ["office"]),
        ("1.0.0+toast", ["toast"]),
        ("1.0.0+post", []),
    ],
)
def test_post_build_metadata_is_only_stripped_once(text, build):
    """str.lstrip("post") used to eat every leading p/o/s/t character."""
    version = Version.parse(text)

    assert version.build == build
    assert version.post is None


@pytest.mark.parametrize(
    "text",
    [
        "1.0.0-",
        "1.0.0+",
        "1.0.0++b",
        "1.0.0-rc..1",
        "1.0.0.",
        "1.0.0 ",
        " 1.0.0",
        "1.0.0-alpha beta",
        "v",
        "abc",
        "",
    ],
)
def test_invalid_versions_are_rejected(text):
    with pytest.raises(ParseVersionError):
        Version.parse(text)


def test_trailing_garbage_becomes_a_prerelease():
    """Garbage is no longer silently treated as build metadata (>= release)."""
    version = Version.parse("1.0.0junk")

    assert version.prerelease == ["junk"]
    assert version < Version.parse("1.0.0")


def test_empty_constraint_equality():
    assert EmptyConstraint() == EmptyConstraint()
    assert not EmptyConstraint() != EmptyConstraint()
    assert EmptyConstraint() != Version.parse("1.0.0")
    assert len({EmptyConstraint(), EmptyConstraint()}) == 1
    assert parse_constraint(">=2,<1") == parse_constraint(">=3,<2")
    assert parse_constraint(">=2,<1") != parse_constraint("*")


def test_version_range_without_max_does_not_crash():
    version_range = VersionRange(
        min=Version.parse("1.0.0"),
        include_min=True,
        always_include_max_prerelease=True,
    )

    assert str(version_range) == ">=1.0.0"
    assert version_range.allows(Version.parse("2.0.0"))

    assert str(VersionRange(always_include_max_prerelease=True)) == "*"


def test_constraints_are_hashable():
    assert isinstance(hash(Version.parse("1.0.0")), int)
    assert isinstance(hash(VersionRange(min=Version.parse("1.0.0"))), int)
    assert isinstance(hash(EmptyConstraint()), int)

    union = parse_constraint("<1.0.0 || >2.0.0")

    assert isinstance(union, VersionUnion)
    assert isinstance(hash(union), int)
    assert len({union, parse_constraint("<1.0.0 || >2.0.0")}) == 1


def test_hash_takes_the_fourth_component_into_account():
    assert hash(Version.parse("1.0.0.1")) != hash(Version.parse("1.0.0.2"))
    assert Version.parse("1.0.0.1") != Version.parse("1.0.0.2")


def test_comparison_with_a_foreign_object_raises_type_error():
    with pytest.raises(TypeError):
        Version.parse("1.0.0") < None

    with pytest.raises(TypeError):
        VersionRange(min=Version.parse("1.0.0")) < None


@pytest.mark.parametrize("constraints", [None, 42, [], {}])
def test_parse_constraint_rejects_non_strings(constraints):
    with pytest.raises(ValueError):
        parse_constraint(constraints)


@pytest.mark.parametrize(
    "text",
    [
        "1.0.0",
        "1.0.0-alpha.1",
        "1.0.0-rc.1.2",
        "1.0.0+build.1",
        "1.0.0-rc.1+build.1",
        "1.2.3.4",
        "1.0",
    ],
)
def test_text_round_trip(text):
    assert Version.parse(str(Version.parse(text))) == Version.parse(text)


def test_huge_numbers_raise_parse_version_error():
    """Python refuses int() on >4300 digits; that must not leak a bare ValueError."""
    for text in ["1" * 5000, "1.0." + "0" * 5000, "1.0.0-" + "1" * 5000]:
        with pytest.raises(ParseVersionError):
            Version.parse(text)

        with pytest.raises(ValueError):
            parse_constraint(">=" + text)


def test_version_and_version_range_are_never_equal():
    """Version subclasses VersionRange, so their hashes can never match."""
    version = Version.parse("1.2.3")
    point_range = VersionRange(version, version, True, True)

    assert version != point_range
    assert point_range != version
    assert len({version, point_range}) == 2


def test_type_information_is_shipped():
    assert os.path.exists(os.path.join(os.path.dirname(semver.__file__), "py.typed"))


def test_constraints_keep_allowing_multi_part_prereleases():
    assert parse_constraint("^1.0.0").allows(Version.parse("1.5.0-rc.1.2"))
    assert parse_constraint(">=1.0.0,<2.0.0").allows(Version.parse("1.5.0-foo"))
    assert not parse_constraint(">=1.0.0").allows(Version.parse("1.0.0-foo"))
