"""Build-stamp constants used by `/api/v1/_version` + the frontend footer.

Bumped on every release so both operators and the main agent can confirm
which bundle production is actually serving (CloudFront + EB caching has
caused repeated "did the deploy land?" debugging rounds).
"""
BUILD_VERSION = "v54g"
BUILD_DATE = "2026-02-17"
