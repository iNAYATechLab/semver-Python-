from .version_constraint import VersionConstraint


class EmptyConstraint(VersionConstraint):
    def is_empty(self):
        return True

    def is_any(self):
        return False

    def allows(self, version):
        return False

    def allows_all(self, other):
        return other.is_empty()

    def allows_any(self, other):
        return False

    def intersect(self, other):
        return self

    def union(self, other):
        return other

    def difference(self, other):
        return self

    def __eq__(self, other):
        if not isinstance(other, EmptyConstraint):
            return NotImplemented

        return True

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return NotImplemented

        return not result

    def __hash__(self):
        return hash(EmptyConstraint)

    def __str__(self):
        return "<empty>"

    def __repr__(self):
        return "<EmptyConstraint>"
