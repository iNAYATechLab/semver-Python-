import re

from typing import List  # noqa: F401  (used in type comments)
from typing import Optional  # noqa: F401  (used in type comments)
from typing import Union  # noqa: F401  (used in type comments)

from .empty_constraint import EmptyConstraint
from .exceptions import ParseVersionError
from .patterns import COMPLETE_VERSION
from .version_constraint import VersionConstraint
from .version_range import VersionRange
from .version_union import VersionUnion

# A trailing "post" marker or a lone integer after the release segment denotes
# a post-release ("1.0.0-post1", "1.0.0-1"), which is greater than the release
# itself. This mirrors the PyPI/PEP 440 convention poetry relies on. Anything
# else found there is a pre-release (SemVer 2.0.0 s9).
POST_RELEASE = re.compile(r"(?i)^(?:post)?[-_.]?(?P<digits>\d+)?$")


def _to_int(text):  # type: (str) -> int
    """int() that reports failures as ParseVersionError.

    Since Python 3.11 int() refuses to convert digit strings longer than 4300
    characters, which would otherwise leak a bare ValueError out of parse().
    """
    try:
        return int(text)
    except ValueError as e:
        raise ParseVersionError("Unable to parse version: {}".format(e))


def _is_valid_identifier_list(text):  # type: (str) -> bool
    """Check a dot separated list of pre-release/build identifiers.

    None of the identifiers may be empty ("rc..1") and none may end with a
    hyphen, which is how a dangling separator such as "1.0.0-" shows up.
    """
    identifiers = text.split(".")

    return all(
        identifier and not identifier.endswith("-") for identifier in identifiers
    )


class Version(VersionRange):
    """
    A parsed semantic version number.
    """

    def __init__(
        self,
        major,  # type: int
        minor=None,  # type: Optional[int]
        patch=None,  # type: Optional[int]
        rest=None,  # type: Optional[int]
        pre=None,  # type: Optional[str]
        build=None,  # type: Optional[str]
        text=None,  # type: Optional[str]
        precision=None,  # type: Optional[int]
        post=None,  # type: Optional[int]
    ):  # type: (...) -> None
        self._major = int(major)
        self._precision = None
        if precision is None:
            self._precision = 1

        if minor is None:
            minor = 0
        else:
            if self._precision is not None:
                self._precision += 1

        self._minor = int(minor)

        if patch is None:
            patch = 0
        else:
            if self._precision is not None:
                self._precision += 1

        if rest is None:
            rest = 0
        else:
            if self._precision is not None:
                self._precision += 1

        if precision is not None:
            self._precision = precision

        self._patch = int(patch)
        self._rest = int(rest)

        if text is None:
            parts = [str(major)]
            if self._precision >= 2 or minor != 0:
                parts.append(str(minor))

                if self._precision >= 3 or patch != 0:
                    parts.append(str(patch))

                if self._precision >= 4 or rest != 0:
                    parts.append(str(rest))

            text = ".".join(parts)
            if pre:
                text += "-{}".format(pre)

            if build:
                text += "+{}".format(build)

        self._text = text

        pre = self._normalize_prerelease(pre)

        self._prerelease = []
        if pre is not None:
            self._prerelease = self._split_parts(pre)

        build = self._normalize_build(build)

        self._build = []
        if build is not None:
            if build.startswith(("-", "+")):
                build = build[1:]

            self._build = self._split_parts(build)

        # A post-release counter (1.0.0-1, 1.0.0-post1, 1.0.0+post1). It is
        # tracked separately from build metadata because it must sort *above*
        # the plain release, while build metadata is ignored (SemVer 2.0.0 s10).
        self._post = post

    @property
    def major(self):  # type: () -> int
        return self._major

    @property
    def minor(self):  # type: () -> int
        return self._minor

    @property
    def patch(self):  # type: () -> int
        return self._patch

    @property
    def rest(self):  # type: () -> int
        return self._rest

    @property
    def prerelease(self):  # type: () -> List[str]
        return self._prerelease

    @property
    def build(self):  # type: () -> List[str]
        return self._build

    @property
    def post(self):  # type: () -> Optional[int]
        """The post-release counter, or None for a plain release."""
        return self._post

    @property
    def text(self):
        return self._text

    @property
    def precision(self):  # type: () -> int
        return self._precision

    @property
    def stable(self):
        if not self.is_prerelease():
            return self

        return self.next_patch

    @property
    def next_major(self):  # type: () -> Version
        if self.is_prerelease() and self.minor == 0 and self.patch == 0:
            return Version(self.major, self.minor, self.patch)

        return self._increment_major()

    @property
    def next_minor(self):  # type: () -> Version
        if self.is_prerelease() and self.patch == 0:
            return Version(self.major, self.minor, self.patch)

        return self._increment_minor()

    @property
    def next_patch(self):  # type: () -> Version
        if self.is_prerelease():
            return Version(self.major, self.minor, self.patch)

        return self._increment_patch()

    @property
    def next_breaking(self):  # type: () -> Version
        if self.major == 0:
            if self.minor != 0:
                return self._increment_minor()

            if self._precision == 1:
                return self._increment_major()
            elif self._precision == 2:
                return self._increment_minor()

            return self._increment_patch()

        return self._increment_major()

    @property
    def first_prerelease(self):  # type: () -> Version
        return Version.parse(
            "{}.{}.{}-alpha.0".format(self.major, self.minor, self.patch)
        )

    @property
    def min(self):
        return self

    @property
    def max(self):
        return self

    @property
    def full_max(self):
        return self

    @property
    def include_min(self):
        return True

    @property
    def include_max(self):
        return True

    @classmethod
    def parse(cls, text):  # type: (str) -> Version
        # fullmatch (and not match) so that trailing garbage such as
        # "1.0.0junk", "1.0.0 " or "1.0.0-" is rejected instead of being
        # silently ignored.
        try:
            match = COMPLETE_VERSION.fullmatch(text)
        except TypeError:
            match = None

        if match is None:
            raise ParseVersionError('Unable to parse "{}".'.format(text))

        text = text.rstrip(".")

        major = _to_int(match.group("major"))
        minor = _to_int(match.group("minor")) if match.group("minor") else None
        patch = _to_int(match.group("patch")) if match.group("patch") else None
        rest = _to_int(match.group("rest")) if match.group("rest") else None

        pre = match.group("pre")
        build = match.group("build")

        if build:
            build = build.lstrip("+")

        # A dangling separator ("1.0.0-", "1.0.0+-") or an empty identifier
        # ("1.0.0-rc..1") must not be accepted: the regex above only sees a
        # valid identifier list at this point, so check it explicitly.
        for identifier in (pre, build):
            if identifier is not None and not _is_valid_identifier_list(identifier):
                raise ParseVersionError('Unable to parse "{}".'.format(text))

        # Post-releases: "1.0.0-1", "1.0.0-post1", "1.0.0+post1".
        post = None
        if pre is not None:
            marker = POST_RELEASE.match(pre)
            if marker and (pre.lower().startswith("post") or pre.isdigit()):
                digits = marker.group("digits")
                post = _to_int(digits) if digits is not None else None
                pre = None

        if build is not None and build.lower().startswith("post"):
            digits = build[4:]
            if not digits or digits.isdigit():
                if digits:
                    post = int(digits)
                build = None

        return Version(major, minor, patch, rest, pre, build, text, post=post)

    def is_any(self):
        return False

    def is_empty(self):
        return False

    def is_prerelease(self):  # type: () -> bool
        return len(self._prerelease) > 0

    def allows(self, version):  # type: (Version) -> bool
        return self == version

    def allows_all(self, other):  # type: (VersionConstraint) -> bool
        return other.is_empty() or other == self

    def allows_any(self, other):  # type: (VersionConstraint) -> bool
        return other.allows(self)

    def intersect(self, other):  # type: (VersionConstraint) -> VersionConstraint
        if other.allows(self):
            return self

        return EmptyConstraint()

    def union(self, other):  # type: (VersionConstraint) -> VersionConstraint
        from .version_range import VersionRange

        if other.allows(self):
            return other

        if isinstance(other, VersionRange):
            if other.min == self:
                return VersionRange(
                    other.min,
                    other.max,
                    include_min=True,
                    include_max=other.include_max,
                )

            if other.max == self:
                return VersionRange(
                    other.min,
                    other.max,
                    include_min=other.include_min,
                    include_max=True,
                )

        return VersionUnion.of(self, other)

    def difference(self, other):  # type: (VersionConstraint) -> VersionConstraint
        if other.allows(self):
            return EmptyConstraint()

        return self

    def equals_without_prerelease(self, other):  # type: (Version) -> bool
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )

    def _increment_major(self):  # type: () -> Version
        return Version(self.major + 1, 0, 0, precision=self._precision)

    def _increment_minor(self):  # type: () -> Version
        return Version(self.major, self.minor + 1, 0, precision=self._precision)

    def _increment_patch(self):  # type: () -> Version
        return Version(
            self.major, self.minor, self.patch + 1, precision=self._precision
        )

    def _normalize_prerelease(self, pre):  # type: (str) -> str
        if not pre:
            return

        m = re.match(r"(?i)^(a|alpha|b|beta|c|pre|rc|dev)[-.]?(\d+)?$", pre)
        if not m:
            # Not a known modifier: keep the identifiers untouched instead of
            # dropping the whole pre-release, which used to turn versions such
            # as "1.0.0-rc.1.2" or "1.0.0-alpha.beta" into stable releases.
            return pre

        modifier = m.group(1)
        number = m.group(2)

        if number is None:
            number = 0

        if modifier == "a":
            modifier = "alpha"
        elif modifier == "b":
            modifier = "beta"
        elif modifier in {"c", "pre"}:
            modifier = "rc"
        elif modifier == "dev":
            modifier = "alpha"

        return "{}.{}".format(modifier, number)

    def _normalize_build(self, build):  # type: (str) -> str
        if not build:
            return

        if build.startswith("post"):
            # Strip the "post" prefix only. str.lstrip() would remove every
            # leading character from the set {p, o, s, t}, turning a build
            # string like "postsponsor" into "nsor".
            build = build[4:]

        if not build:
            return

        return build

    def _split_parts(self, text):  # type: (str) -> List[Union[str, int]]
        parts = text.split(".")

        for i, part in enumerate(parts):
            try:
                parts[i] = int(part)
            except (TypeError, ValueError):
                continue

        return parts

    def __lt__(self, other):
        comparison = self._cmp(other)
        if comparison is NotImplemented:
            return NotImplemented

        return comparison < 0

    def __le__(self, other):
        comparison = self._cmp(other)
        if comparison is NotImplemented:
            return NotImplemented

        return comparison <= 0

    def __gt__(self, other):
        comparison = self._cmp(other)
        if comparison is NotImplemented:
            return NotImplemented

        return comparison > 0

    def __ge__(self, other):
        comparison = self._cmp(other)
        if comparison is NotImplemented:
            return NotImplemented

        return comparison >= 0

    def _cmp(self, other):
        if not isinstance(other, VersionConstraint):
            return NotImplemented

        if not isinstance(other, Version):
            return -other._cmp(self)

        if self.major != other.major:
            return self._cmp_parts(self.major, other.major)

        if self.minor != other.minor:
            return self._cmp_parts(self.minor, other.minor)

        if self.patch != other.patch:
            return self._cmp_parts(self.patch, other.patch)

        if self.rest != other.rest:
            return self._cmp_parts(self.rest, other.rest)

        # Pre-releases always come before no pre-release string.
        if not self.is_prerelease() and other.is_prerelease():
            return 1

        if not other.is_prerelease() and self.is_prerelease():
            return -1

        comparison = self._cmp_lists(self.prerelease, other.prerelease)
        if comparison != 0:
            return comparison

        # A post-release sorts above the plain release it follows.
        if self.post != other.post:
            if self.post is None:
                return -1

            if other.post is None:
                return 1

            return self._cmp_parts(self.post, other.post)

        # Build metadata MUST be ignored when determining version precedence
        # (SemVer 2.0.0 s10): "1.0.0+a" and "1.0.0+b" have the same precedence.
        return 0

    def _cmp_parts(self, a, b):
        if a < b:
            return -1
        elif a > b:
            return 1

        return 0

    def _cmp_lists(self, a, b):  # type: (List, List) -> int
        for i in range(max(len(a), len(b))):
            a_part = None
            if i < len(a):
                a_part = a[i]

            b_part = None
            if i < len(b):
                b_part = b[i]

            if a_part == b_part:
                continue

            # Missing parts come after present ones.
            if a_part is None:
                return -1

            if b_part is None:
                return 1

            if isinstance(a_part, int):
                if isinstance(b_part, int):
                    return self._cmp_parts(a_part, b_part)

                return -1
            else:
                if isinstance(b_part, int):
                    return 1

                return self._cmp_parts(a_part, b_part)

        return 0

    def __eq__(self, other):  # type: (Version) -> bool
        if not isinstance(other, Version):
            return NotImplemented

        # Build metadata is not part of a version's identity: "1.0.0+a" and
        # "1.0.0+b" are the same version as far as precedence is concerned
        # (SemVer 2.0.0 s10).
        return (
            self._major == other.major
            and self._minor == other.minor
            and self._patch == other.patch
            and self._rest == other.rest
            and self._prerelease == other.prerelease
            and self._post == other.post
        )

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return NotImplemented

        return not result

    def __str__(self):
        return self._text

    def __repr__(self):
        return "<Version {}>".format(str(self))

    def __hash__(self):
        return hash(
            (
                self.major,
                self.minor,
                self.patch,
                self.rest,
                ".".join(str(p) for p in self.prerelease),
                self.post,
            )
        )
