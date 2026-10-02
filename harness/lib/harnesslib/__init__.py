"""Shared library for the harness media tools (colour, tokens, type, schemas, art direction).

Installed at .claude/harness/lib/harnesslib/ (web and mobile profiles). Skill scripts import it
with the one bootstrap documented in .claude/harness/lib/README.md; nothing else may import it.
Every module is stdlib only, except harnesslib.imaging, which needs Pillow.
"""

API_VERSION = 1

# Exit codes shared by every media CLI (see lib/README.md).
EXIT_OK = 0          # completed (a report may still say REVIEW REQUIRED or SKIPPED)
EXIT_FAIL = 1        # failed validation or an unmet production gate
EXIT_OPERATIONAL = 2  # invalid invocation, missing dependency or operational failure
