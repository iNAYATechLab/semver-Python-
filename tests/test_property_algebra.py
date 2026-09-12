"""
Property tests over the range algebra: for every pair of constraints and a
grid of versions, intersect/union/difference must behave like the equivalent
set operations, and str() must round-trip.
"""

import itertools

import pytest

from semver import parse_constraint

VERSIONS = [
    "0.9.0",
    "1.0.0-alpha",
    "1.0.0-beta",
    "1.0.0",
    "1.0.0+build",
    "1.2.3",
    "1.5.0",
    "1.5.0-rc.1",
    "1.5.0-rc.1.2",
    "1.9.9",
    "2.0.0-alpha",
    "2.0.0",
    "3.1.4",
]

CONSTRAINTS = [
    "*",
    "<1.0.0",
    ">1.0.0",
    ">=1.0.0",
    "<=2.0.0",
    "!=1.5.0",
    "^1.0.0",
    "~1.0.0",
    "1.x",
    "1.0.0",
    ">=1.0.0,<2.0.0",
    "<1.0.0 || >2.0.0",
    ">1.5.0,<3.0.0",
]

PAIRS = list(itertools.product(CONSTRAINTS, repeat=2))


@pytest.mark.parametrize("left,right", PAIRS)
def test_intersect_is_a_logical_and(left, right):
    first, second = parse_constraint(left), parse_constraint(right)

    for text in VERSIONS:
        version = parse_constraint(text)

        assert first.intersect(second).allows(version) == (
            first.allows(version) and second.allows(version)
        ), (left, right, text)


@pytest.mark.parametrize("left,right", PAIRS)
def test_union_is_a_logical_or(left, right):
    first, second = parse_constraint(left), parse_constraint(right)

    for text in VERSIONS:
        version = parse_constraint(text)

        assert first.union(second).allows(version) == (
            first.allows(version) or second.allows(version)
        ), (left, right, text)


@pytest.mark.parametrize("left,right", PAIRS)
def test_difference_is_a_logical_and_not(left, right):
    first, second = parse_constraint(left), parse_constraint(right)

    for text in VERSIONS:
        version = parse_constraint(text)

        assert first.difference(second).allows(version) == (
            first.allows(version) and not second.allows(version)
        ), (left, right, text)


@pytest.mark.parametrize("constraints", CONSTRAINTS)
def test_constraints_round_trip_through_str(constraints):
    parsed = parse_constraint(constraints)

    for text in VERSIONS:
        version = parse_constraint(text)

        assert parse_constraint(str(parsed)).allows(version) == parsed.allows(
            version
        ), (constraints, text)


@pytest.mark.parametrize("constraints", CONSTRAINTS)
def test_constraints_are_stable_under_double_inversion(constraints):
    parsed = parse_constraint(constraints)

    for text in VERSIONS:
        version = parse_constraint(text)

        inverted = parse_constraint("*").difference(parsed)

        assert inverted.allows(version) == (not parsed.allows(version))
