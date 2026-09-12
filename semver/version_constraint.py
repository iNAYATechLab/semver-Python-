from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import semver  # noqa: F401  (used in type comments)


class VersionConstraint:
    def is_empty(self):  # type: () -> bool
        raise NotImplementedError()

    def is_any(self):  # type: () -> bool
        raise NotImplementedError()

    def allows(self, version):  # type: (semver.Version) -> bool
        raise NotImplementedError()

    def allows_all(self, other):  # type: (VersionConstraint) -> bool
        raise NotImplementedError()

    def allows_any(self, other):  # type: (VersionConstraint) -> bool
        raise NotImplementedError()

    def intersect(self, other):  # type: (VersionConstraint) -> VersionConstraint
        raise NotImplementedError()

    def union(self, other):  # type: (VersionConstraint) -> VersionConstraint
        raise NotImplementedError()

    def difference(self, other):  # type: (VersionConstraint) -> VersionConstraint
        raise NotImplementedError()
