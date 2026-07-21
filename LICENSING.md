# Repository Licensing

Fluxy has explicit file-level license boundaries. A commercial subscription does not replace or restrict the open-source licenses below.

| Material | License | Copyright holder |
| --- | --- | --- |
| `src/fluxy/`, `ignition_webdev/`, Python tests, Python documentation, and Python distribution | MIT | As stated in the root `LICENSE` and file history |
| Authored files under `ignition-module/`, including `fluxy_dispatch.py` | Mozilla Public License 2.0 | Green Pipe Partners, LLC, as recorded in `ignition-module/PROVENANCE.md` |
| Gradle wrapper scripts and wrapper JAR | Apache License 2.0 | Gradle authors; not relicensed by Green Pipe Partners |
| Ignition SDK and host-provided libraries | Their respective licenses | Their respective owners; not bundled in the Fluxy module |

The Python wheel and source distribution intentionally exclude `ignition-module/`. The Gateway module embeds its own MPL-2.0 license, notice, corresponding-source instructions, and SBOM.

## Fluxy Official

Green Pipe Partners may sell signed official module binaries, Ignition activation, maintenance releases, support, installation convenience, and contractual services. Those services do not remove recipients' MPL-2.0 rights in module source already released.

An independently built fork may remove or modify licensing checks as permitted by MPL-2.0. It does not receive Green Pipe Partners' signing certificate, activation service, update channel, support, warranties, service levels, or permission to represent the fork as an official Fluxy release.

Previously entitled official versions are intended to continue operating permanently. Maintenance controls access to newer entitled versions and support, not continued operation of a previously entitled version.

This file describes repository policy and is not a substitute for legal advice or a commercial contract.
