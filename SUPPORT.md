# Support

## Where to ask

**Open an issue:
[github.com/a-hikata/eo-claim-lint/issues](https://github.com/a-hikata/eo-claim-lint/issues)**

Use issues for all of the following:

- General questions about how to use the linter or the Action.
- Bug reports.
- **False positives** — a rule reported something that is actually fine.
- **False negatives** — a document that should have been reported and was not.
- Feature requests, including proposals for new rules.

False positives and false negatives are the most useful reports this project can
receive. A rule that fires on correct documents trains people to ignore it, and
a rule that never fires proves nothing. Both are worth an issue.

## Security vulnerabilities do not go here

**Never report a vulnerability through a public issue.**

Use
[private vulnerability reporting](https://github.com/a-hikata/eo-claim-lint/security/advisories/new)
instead — the repository's **Security** tab, then **Report a vulnerability**.
The report stays visible only to you and the maintainer until a fix is
published.

See [SECURITY.md](SECURITY.md) for what is in scope, what to include, and what
to leave out.

## What not to put in a report

**Do not include secrets, credentials, tokens, personal data, customer data, or
sensitive real-world coordinates** in an issue, a pull request, or a
reproduction case. This applies to ordinary bug reports as much as to security
reports — an issue is public and permanent, and a value pasted into one cannot
be reliably withdrawn.

**Reproduce with synthetic data.** Invented place names, synthetic coordinates,
and `urn:example:` identifiers are enough to demonstrate any rule in this
project; the repository's own fixtures are built that way and are a good
starting point. If you genuinely cannot build a reproduction from synthetic
data, say so in the report rather than pasting the real thing, and we will work
out how to handle it.

## Supported versions

**Only the latest `0.x` release line is actively supported.** While the version
is `0.x`, fixes go into the newest release and there are no backports. See
[SECURITY.md](SECURITY.md) for the same table applied to security fixes.

## What to expect

**Support is provided on a best-effort basis. No response time is guaranteed.**
This is a personal open source project maintained alongside other work. Issues
are read, but an answer may take a while, and some requests will be declined —
particularly rules that cannot be evaluated from a single claim document, or
that depend on one organisation's domain thresholds.

Nothing here creates an obligation of support, and nothing here modifies the
[Apache License 2.0](LICENSE), under which this software is provided **without
warranties or conditions of any kind**.

## Contributing a fix

Patches are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the development
setup, the checks a pull request has to pass, and the rule that matters most:
never add real-world locations or personal data to this repository.

## Related documents

- [SECURITY.md](SECURITY.md) — vulnerability reporting and scope
- [CONTRIBUTING.md](CONTRIBUTING.md) — development and pull requests
- [PRIVACY.md](PRIVACY.md) — what this project does and does not process
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — conduct and private reporting
- [LICENSE](LICENSE) — Apache License 2.0
