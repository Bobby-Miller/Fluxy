// SPDX-FileCopyrightText: 2026 Green Pipe Partners, LLC
// SPDX-License-Identifier: MPL-2.0

plugins {
    `java-library`
}

val moduleVersion = rootProject.extra["fluxyModuleVersion"] as String
val buildNumber = rootProject.extra["fluxyBuildNumber"] as String
val repositoryUrl = rootProject.extra["fluxyRepositoryUrl"] as String
val sourceCommit = rootProject.extra["fluxySourceCommit"] as String
val sourceTag = rootProject.extra["fluxySourceTag"] as String
val licenseMode = rootProject.extra["fluxyLicenseMode"] as String

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(17))
    }
}

dependencies {
    compileOnly("com.inductiveautomation.ignitionsdk:ignition-common:8.1.50")
    compileOnly("com.inductiveautomation.ignitionsdk:gateway-api:8.1.50")
    compileOnly("com.inductiveautomation.ignition:ia-gson:2.10.1")
    testImplementation("com.inductiveautomation.ignitionsdk:ignition-common:8.1.50")
    testImplementation("org.junit.jupiter:junit-jupiter:5.11.4")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
    options.release.set(17)
}

tasks.compileJava {
    source("../gateway/src/main/java/com/greenpipepartners/fluxy/gateway/HistorianStream.java")
}

tasks.compileTestJava {
    source("../gateway/src/test/java/com/greenpipepartners/fluxy/gateway/HistorianStreamTest.java")
}

tasks.processResources {
    dependsOn(rootProject.tasks.named("generateCompliance"))
    inputs.properties(
        "moduleVersion" to moduleVersion,
        "sourceCommit" to sourceCommit,
        "sourceTag" to sourceTag,
        "sourceRepository" to repositoryUrl,
        "licenseMode" to licenseMode,
    )
    filesMatching("fluxy-build.properties") {
        expand(
            "moduleVersion" to moduleVersion,
            "sourceCommit" to sourceCommit,
            "sourceTag" to sourceTag,
            "sourceRepository" to repositoryUrl,
            "licenseMode" to licenseMode,
        )
    }
    from(rootProject.layout.projectDirectory.file("LICENSE")) {
        into("META-INF")
        rename { "LICENSE" }
    }
    from(rootProject.layout.projectDirectory.file("NOTICE")) {
        into("META-INF")
    }
    from(rootProject.layout.projectDirectory.file("THIRD_PARTY_NOTICES.md")) {
        into("META-INF")
    }
    from(rootProject.layout.projectDirectory.file("WEBDEV_MIT_NOTICE")) {
        into("META-INF")
    }
    from(rootProject.layout.buildDirectory.dir("generated/compliance")) {
        into("META-INF")
    }
}

tasks.jar {
    manifest {
        attributes(
            "Implementation-Title" to "Fluxy",
            "Implementation-Version" to moduleVersion,
            "Implementation-Vendor" to "Green Pipe Partners, LLC",
            "Bundle-License" to "MPL-2.0",
            "Build-Number" to buildNumber,
            "Git-Commit" to sourceCommit,
            "Source-Tag" to sourceTag,
            "Source-URL" to repositoryUrl,
            "Ignition-Version" to "8.1.50+",
            "Fluxy-License-Mode" to licenseMode,
        )
    }
}

tasks.withType<AbstractArchiveTask>().configureEach {
    isPreserveFileTimestamps = false
    isReproducibleFileOrder = true
}

tasks.test {
    useJUnitPlatform()
    systemProperty("fluxy.test.expectedLicenseMode", licenseMode)
}

tasks.processTestResources {
    from("../gateway/src/test/resources")
}
