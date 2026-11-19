package io.github.mohdzain98.gnost;

import java.util.Locale;

/** Maps the JVM's operating system and CPU names to a GNOST release platform key. */
final class Platform {

    private Platform() {
    }

    /** The key of the binary for this platform (as in the release file names), or null. */
    static String key(String osName, String osArch) {
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
            return "win32-x64";
        }
        return null;
    }

    static boolean isWindows(String osName) {
        return osName != null && osName.toLowerCase(Locale.ROOT).contains("windows");
    }

    /** The key for the JVM this code is running in. */
    static String current() {
        return key(System.getProperty("os.name"), System.getProperty("os.arch"));
    }

    /** Release archive extension: zip on Windows, tar.gz elsewhere. */
    static String archiveExtension(String key) {
        return key.startsWith("win32") ? "zip" : "tar.gz";
    }

    /** File name of the release archive, such as gnost-0.5.3-linux-x64.tar.gz. */
    static String archiveName(String releaseVersion, String key) {
        return "gnost-" + releaseVersion + "-" + key + "." + archiveExtension(key);
    }
}
