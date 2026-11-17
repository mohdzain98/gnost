package io.github.mohdzain98.gnost;

import java.util.Locale;

/** Maps the JVM's operating system and CPU names to a GNOST binary classifier. */
final class Platform {

    private Platform() {
    }

    /** The classifier of the binary for this platform, or null if there is none. */
    static String classifier(String osName, String osArch) {
        String os = osName == null ? "" : osName.toLowerCase(Locale.ROOT);
        String arch = osArch == null ? "" : osArch.toLowerCase(Locale.ROOT);
        boolean arm64 = arch.equals("aarch64") || arch.equals("arm64");
        boolean x64 = arch.equals("amd64") || arch.equals("x86_64") || arch.equals("x64");
        if ((os.contains("mac") || os.contains("darwin")) && arm64) {
            return "darwin-arm64";
        }
        if (os.contains("linux") && x64) {
            return "linux-x64";
        }
        if (os.contains("windows") && x64) {
            return "windows-x64";
        }
        return null;
    }

    static boolean isWindows(String osName) {
        return osName != null && osName.toLowerCase(Locale.ROOT).contains("windows");
    }

    /** The classifier for the JVM this code is running in. */
    static String current() {
        return classifier(System.getProperty("os.name"), System.getProperty("os.arch"));
    }
}
