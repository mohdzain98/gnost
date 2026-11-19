package io.github.mohdzain98.gnost;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import java.util.Properties;
import org.junit.Test;

public class PluginInfoTest {

    @Test
    public void filledInValuesAreUsed() {
        Properties p = new Properties();
        p.setProperty("version", "0.5.3");
        p.setProperty("release.version", "0.5.3");
        p.setProperty("sha.linux-x64", "ABC123");
        PluginInfo info = new PluginInfo(p);
        assertEquals("0.5.3", info.version());
        assertEquals("0.5.3", info.releaseVersion());
        assertEquals("abc123", info.sha256("linux-x64"));
    }

    @Test
    public void unfilledPlaceholdersCountAsMissing() {
        Properties p = new Properties();
        p.setProperty("version", "0.5.3-SNAPSHOT");
        p.setProperty("release.version", "${gnost.release.version}");
        p.setProperty("sha.linux-x64", "${gnost.sha.linux-x64}");
        PluginInfo info = new PluginInfo(p);
        assertNull(info.releaseVersion());
        assertNull(info.sha256("linux-x64"));
        assertNull(info.sha256("darwin-arm64"));
    }

    @Test
    public void thePackagedPropertiesFileLoads() throws Exception {
        assertEquals(false, PluginInfo.load().version() == null);
    }
}
