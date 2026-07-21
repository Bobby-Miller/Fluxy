<!-- SPDX-FileCopyrightText: 2026 Green Pipe Partners, LLC -->
<!-- SPDX-License-Identifier: MPL-2.0 -->

# Provenance And Ownership Record

This record documents the completed assignment of existing Fluxy rights and the remaining release gates.

## Audit Result

- Repository history currently contains one identified individual author: Bobby Miller (`miller.bobby@gmail.com`).
- The Gateway module was introduced before its first repository commit and therefore has no independent Git blame history yet.
- `gateway/src/main/resources/fluxy_dispatch.py` adapts behavior from the repository's existing MIT-licensed WebDev implementation.
- No non-boilerplate external source copying was identified during the July 11, 2026 review.
- Module structure and lifecycle code use ordinary Ignition SDK and Gradle conventions. Similar API boilerplate exists in public Inductive Automation examples, whose repository-level license was not established by this audit.
- No third-party runtime library is bundled in the current JAR or `.modl`.
- Filesystem ownership, AI assistance, or vendor metadata do not establish copyright ownership.

This is a reasonable engineering provenance review, not a legal opinion or a guarantee that no similar external code exists.

## Author Confirmation

On July 11, 2026, Bobby Miller confirmed that:

- He is the sole individual author and current owner of the copyrightable Fluxy material being assigned.
- No employer, client, contractor, or other person owns any portion of that authored material.
- No third-party example or other externally owned source was copied into the authored Fluxy implementation.
- Gradle, the Ignition SDK, host-provided dependencies, generated files, and other third-party materials are excluded from this ownership statement and retain their respective licenses.

This confirmation resolved the known competing-owner question. The signed assignment below completed the transfer of Assignor-owned existing Fluxy rights.

## Completed Assignment

Robert Miller, also known as Bobby Miller, executed a present assignment to Green Pipe Partners, LLC covering the pre-release module, the MIT WebDev material relicensed into the module, and the other Assignor-owned Fluxy work described by the agreement. No other existing individual or organizational copyright owner is identified.

The confidential executed agreement is stored outside the repository. Public verification evidence is recorded here without publishing signatures or personal details:

| Assignor | Assignee | Covered material | Execution date | Internal reference | Status |
| --- | --- | --- | --- | --- | --- |
| Robert Miller (Bobby Miller) | Green Pipe Partners, LLC | Assignor-owned Fluxy work through the effective date | July 11, 2026 | `GPP-IP-2026-001` | Complete |

Executed document SHA-256:

```text
71d4df2038b6888b1dfcc16b5cb9ef1c98028e7fd11e3fbbc69a2cae133b2052
```

Exhibit A identifies the historical repository as `https://github.com/Bobby-Miller/Fluxy`; the repository is currently controlled at `https://github.com/GreenPipePartners/Fluxy`. The agreement expressly includes work maintained elsewhere and the Assignor confirmed this is the correct executed document.

The form in `../legal/COPYRIGHT_ASSIGNMENT_TEMPLATE.md` remains an unused drafting template. The executed agreement identified above controls.

## Future Work

The completed assignment covers Assignor-owned work through its July 11, 2026 effective date. Green Pipe Partners should maintain a continuing founder, employee, or invention-assignment agreement for later work, or execute additional confirmatory assignments when needed. External contributions remain subject to the CLA gate below.

## Contribution Gate

Do not merge an external contribution to `ignition-module/` until the company CLA process is operational and the contributor's individual or corporate CLA is recorded. See `../CONTRIBUTING.md` and `../legal/cla/`.
