import re

# The release segment: major.minor.patch plus an optional fourth component
# ("rest"), which is a poetry extension used by versions such as 1.2.3.4.
_RELEASE = (
    r"v?(?P<major>\d+)"
    r"(?:\.(?P<minor>\d+))?"
    r"(?:\.(?P<patch>\d+))?"
    r"(?:\.(?P<rest>\d+))?"
)

# Pre-release identifiers are dot separated alphanumeric identifiers, e.g.
# "1.0.0-rc.1", "1.0.0-alpha.beta", "1.0.0-x.7.z.92", "1.0.0rc1", "1.0.0_1".
# They may follow the release segment directly or after a "-", "_" or "."
# separator. The first character must be alphanumeric so that a dangling
# separator such as "1.0.0-" is rejected instead of being parsed as "-".
_PRERELEASE = r"(?:[-_.]?(?P<pre>[0-9A-Za-z][0-9A-Za-z-]*(?:\.[0-9A-Za-z-]+)*))?"

# Build metadata always starts with "+", which is what distinguishes it from a
# pre-release: "1.0.0-alpha" is a pre-release, "1.0.0+alpha" is not.
_BUILD = r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"

_COMPLETE_VERSION = _RELEASE + _PRERELEASE + _BUILD

_OPERATOR = r"(?P<op><>|!=|>=?|<=?|==?)?"

COMPLETE_VERSION = re.compile(r"(?i)" + _COMPLETE_VERSION)

CARET_CONSTRAINT = re.compile(r"(?i)^\^(?P<version>{})$".format(_COMPLETE_VERSION))
TILDE_CONSTRAINT = re.compile(r"(?i)^~(?!=)(?P<version>{})$".format(_COMPLETE_VERSION))
TILDE_PEP440_CONSTRAINT = re.compile(
    r"(?i)^~=(?P<version>{})$".format(_COMPLETE_VERSION)
)
X_CONSTRAINT = re.compile(
    r"^(?P<op>!=|==)?\s*v?(?P<major>\d+)"
    r"(?:\.(?P<minor>\d+))?(?:\.(?P<patch>\d+))?"
    r"(?:\.[xX*])+$"
)
BASIC_CONSTRAINT = re.compile(
    r"(?i)^" + _OPERATOR + r"\s*(?P<version>{}|dev)$".format(_COMPLETE_VERSION)
)
