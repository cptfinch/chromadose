# Security Policy

## Scope

chromadose is research software for radiochromic film dosimetry. See
[DISCLAIMER.md](DISCLAIMER.md) — it is not a medical device and is not
intended for clinical use.

This policy covers two categories of issue:

1. **Software security vulnerabilities** — typical CVE-class issues
   (arbitrary code execution, path traversal, dependency vulnerabilities,
   denial of service via malformed input, etc.).
2. **Numerical correctness defects** — bugs that could cause materially
   incorrect dose values, gamma results, or uncertainty estimates.
   Because chromadose may be used in research that informs downstream
   work, accuracy defects are treated with similar seriousness to
   security issues.

## Supported versions

Only the latest released version on PyPI receives fixes. Pin a specific
version in any reproducible work.

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅        |
| < 1.0   | ❌        |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report privately via one of:

- GitHub Security Advisories — "Report a vulnerability" button on the
  repository Security tab (preferred).
- Email the maintainer listed in `pyproject.toml`.

Please include:

- A description of the issue and its impact
- Steps to reproduce (minimal example, input data if safe to share)
- Affected version(s)
- Any suggested fix or mitigation

You can expect:

- Acknowledgement within 7 days
- An initial assessment within 14 days
- Coordinated disclosure once a fix is available, with credit to the
  reporter unless anonymity is requested

## Reporting a numerical correctness defect

Numerical bugs may be reported publicly via a normal GitHub issue,
**unless** you believe the defect could have caused a downstream
clinical or safety impact in a real environment — in which case
please use the private channels above so it can be triaged before
public discussion.

When reporting, please include:

- Method affected (Micke / Mayer / Multigaussian / ANN)
- Inputs (calibration, scan, parameters) — synthetic reproducer preferred
- Expected vs observed output
- Reference (paper, alternative implementation, phantom measurement)

## Out of scope

- Clinical fitness-for-purpose questions — these are the responsibility
  of the medical physicist deploying the software, not the chromadose
  authors. See DISCLAIMER.md.
- Vulnerabilities in upstream dependencies — please report those to the
  relevant project. We will update pins promptly once fixes are available.
