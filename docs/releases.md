# Releases

Before enabling releases, check the package version and name availability again,
configure the dedicated release App ID as `RELEASE_APP_ID` and its organisation
Actions key secret as `RELEASE_APP_PRIVATE_KEY`. Grant the App only Contents write,
Pull requests write and Metadata read, with no ruleset bypass. Release-please opens
a release PR; required checks and owner approval apply before merge.

Configure a protected `release` environment with owner approval.
Register the PyPI trusted publisher for this repository, `release.yml`, and
that environment. The workflow builds wheel/sdist, attests both, and uses OIDC
trusted publishing, with no long-lived PyPI token.

Do not enable App auto-merge or add it as a bypass actor. The templates cannot
enforce remote rulesets: verify required checks and code-owner approval using the
organisation baseline before the first public push or real release.

Before the first public push, bind public-text.yml to a reviewed public workflow
commit and review the exact file list and fresh tree/history secret scans. An
offline extraction with a private workflow SHA proves no public enforcement.
Configure the pending PyPI publisher for alertshadow, release.yml and the protected
release environment. Internal consumers and script deletion wait for a release.
