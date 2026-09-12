# SemVer Python

A semantic versioning library for Python.

It parses versions and version constraints (`^1.2.3`, `~1.2`, `>=1.0,<2.0`,
`1.x`, `!=1.5.0`, `*`), and answers the questions a resolver asks: does this
version satisfy that constraint, and how do two versions compare?

## Install

```bash
pip install poetry-semver
```

## Usage

```python
from semver import Version, parse_constraint

version = Version.parse("1.2.3-rc.1+build.5")

version.major          # 1
version.minor          # 2
version.patch          # 3
version.prerelease     # ['rc', 1]
version.build          # ['build', 5]
version.is_prerelease  # True
version.stable         # <Version 1.2.3>
version.next_breaking  # <Version 2.0.0>
str(version)           # '1.2.3-rc.1+build.5'

constraint = parse_constraint("^1.2.3")

str(constraint)                     # '>=1.2.3,<2.0.0'
constraint.allows(Version.parse("1.9.9"))       # True
constraint.allows(Version.parse("2.0.0"))       # False
constraint.allows(Version.parse("1.5.0-rc.1"))  # True

# Set algebra over constraints
a, b = parse_constraint(">=1.0.0"), parse_constraint("<2.0.0")
str(a.intersect(b))   # '>=1.0.0,<2.0.0'
str(a.difference(b))  # '>=2.0.0'
str(a.union(parse_constraint(">3.0.0")))  # '>=1.0.0 || >3.0.0'
```

## Behaviour notes

These are the rules that are easy to get wrong, so they are spelled out here:

- **Pre-releases are kept, never dropped.** `1.0.0-rc.1.2`, `1.0.0-1.2.3`,
  `1.0.0-foo` and `1.0.0-alpha.beta` are all pre-releases, and a pre-release
  always sorts **below** the corresponding release (`1.0.0-rc.1 < 1.0.0`),
  as required by [SemVer 2.0.0 §9](https://semver.org/spec/v2.0.0.html).
- **Post-releases are the one exception.** A lone integer or a `post` marker
  after the release segment (`1.0.0-1`, `1.0.0-post1`) keeps the PyPI/PEP 440
  meaning of a post-release, so it sorts **above** `1.0.0`. This is inherited
  from poetry and is preserved deliberately.
- **Build metadata is ignored for precedence** (`SemVer 2.0.0 §10`):
  `1.0.0+a == 1.0.0+b`, and `>=1.0.0+b` allows `1.0.0`. The metadata itself is
  still available through `.build` and `str()`.
- **Parsing is strict.** Trailing garbage and dangling separators are rejected:
  `1.0.0junk` is a pre-release (it has a separator-free identifier), but
  `1.0.0-`, `1.0.0+`, `1.0.0.`, `1.0.0-rc..1` and `" 1.0.0"` raise
  `ParseVersionError`. Leading zeros (`01.02.03`) remain accepted for
  backwards compatibility.

## Development

```bash
pip install pytest pytest-cov
pytest tests/ --cov=semver --cov-report=term-missing   # 690+ tests

tox                # run the suite on Python 3.9 - 3.13 plus the linters
tox -e lint        # flake8 + black --check + isort --check-only
pre-commit install # run the same checks on every commit
```

The suite mixes unit tests, SemVer 2.0.0 compliance tests
(`tests/test_spec_compliance.py`) and property tests over the range algebra
(`tests/test_property_algebra.py`).

## License

MIT — see [LICENSE](LICENSE).
