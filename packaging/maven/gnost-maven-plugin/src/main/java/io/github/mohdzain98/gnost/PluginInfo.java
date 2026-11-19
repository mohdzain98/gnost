package io.github.mohdzain98.gnost;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

/**
 * What the plugin knows about itself, filled in at build time: its own version, the
 * GNOST release it downloads, and the SHA-256 of that release's archives.
 */
final class PluginInfo {

    private final Properties props;

    PluginInfo(Properties props) {
        this.props = props;
    }

    static PluginInfo load() throws IOException {
        Properties p = new Properties();
        try (InputStream in = PluginInfo.class.getResourceAsStream("/gnost-plugin.properties")) {
            if (in == null) {
                throw new IOException("gnost-plugin.properties is missing from the plugin");
            }
            p.load(in);
        }
        return new PluginInfo(p);
    }

    /** The plugin (Maven) version. */
    String version() {
        return value("version");
    }

    /** The GNOST release (as in gnost version and the release tag) or null in a local build. */
    String releaseVersion() {
        return value("release.version");
    }

    /** SHA-256 of the release archive for a platform key, or null if none was built in. */
    String sha256(String key) {
        String v = value("sha." + key);
        return v == null ? null : v.toLowerCase(java.util.Locale.ROOT);
    }

    /** A filtered value; a placeholder that Maven did not fill in counts as missing. */
    private String value(String name) {
        String v = props.getProperty(name);
        if (v == null || v.trim().isEmpty() || v.startsWith("${")) {
            return null;
        }
        return v.trim();
    }
}
