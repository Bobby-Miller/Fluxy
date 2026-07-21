<!-- SPDX-FileCopyrightText: 2026 Green Pipe Partners, LLC -->
<!-- SPDX-License-Identifier: MPL-2.0 -->

# Gateway Module Release

Official module releases are blocked until every item in this document is satisfied. `packageOfficial` enforces the checks that can be automated locally.

## Required Inputs

- IA-assigned `vendorId` for `com.greenpipepartners.fluxy`; replace the committed development value `0` only after assignment.
- IA third-party licensing access and documented version-entitlement parameters.
- CA-issued RSA code-signing certificate whose leaf subject uses `CN=Green Pipe Partners, LLC`.
- Private key in an HSM or equivalent controlled signing service; do not store credentials in Git or Gradle files.
- Clean Git worktree at a reviewed, pushed, immutable tag.
- Executed copyright assignment recorded as required by `../PROVENANCE.md`.
- Counsel-approved CLA, trademark, subscription, support, and activation terms.

## Source Identity

Use a module-specific tag such as `ignition-module-v0.1.3.20260711`. Enable immutable GitHub releases. The exact 40-character commit is embedded in the JAR manifest, build metadata, `SOURCE.txt`, and SBOM.

Official artifacts must link to:

```text
https://github.com/GreenPipePartners/Fluxy/tree/<commit>/ignition-module
https://github.com/GreenPipePartners/Fluxy/archive/<commit>.tar.gz
```

Keep that source available after maintenance expires.

## Build

Development verification:

```bash
JAVA_HOME=/path/to/jdk17 ./gradlew -PignitionTarget=8.1 clean test packageDevelopment
JAVA_HOME=/path/to/jdk17 ./gradlew -PignitionTarget=8.3 clean test packageDevelopment
JAVA_HOME=/path/to/jdk17 ./gradlew -PignitionTarget=8.1 -PlicenseMode=free clean test packageDevelopment
JAVA_HOME=/path/to/jdk17 ./gradlew -PignitionTarget=8.3 -PlicenseMode=free clean test packageDevelopment
```

Official signing uses the IA Gradle plugin's signing properties plus:

```bash
JAVA_HOME=/path/to/jdk17 ./gradlew -PignitionTarget=<8.1-or-8.3> clean packageOfficial \
  -PofficialRelease=true \
  -PsourceCommit=<40-character-commit> \
  -PsourceTag=ignition-module-v0.1.3.20260711
```

The signing keystore, certificate chain, aliases, and passwords must be supplied through the controlled release environment. The build fails if the worktree is dirty, the tag and commit differ, the source identity is incomplete, or `vendorId` remains zero.

## Verification

- Confirm `PROVENANCE.md` has no unresolved release-blocking assignment.
- Review authored files for external copied material and update `THIRD_PARTY_NOTICES.md`.
- Build the Python wheel and sdist and confirm they contain no `ignition-module/`, MPL license, `.modl`, JAR, or module SBOM.
- Confirm the JAR and `.modl` contain MPL license, notice, exact source instructions, source commit/tag, SBOM, and dependency notices.
- Compare two isolated unsigned builds before claiming reproducibility.
- Generate and sign SHA-256 checksums and provenance attestations.
- Scan the repository and artifacts for credentials, private keys, customer data, and secrets.
- Test installation without unsigned-module mode on each supported Ignition version.
- Test active trial, expired trial, reset trial, activated license, invalid/free state, restart, upgrade, uninstall, online activation, offline activation, unactivation, and redundant Gateway behavior.
- Verify entitled purchased versions continue after maintenance ends and newer versions require the intended entitlement.
- Confirm the certificate chain, leaf certificate CN, module ID, vendor ID, and Modules-page display.
- Publish immutable source tag/archive, signed module, checksums, SBOM, provenance, compatibility, and support terms together.

Do not describe a module as IA-certified, approved, or endorsed unless IA has expressly authorized that statement.
