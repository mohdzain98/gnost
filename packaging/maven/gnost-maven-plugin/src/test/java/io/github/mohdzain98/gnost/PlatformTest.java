package io.github.mohdzain98.gnost;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class PlatformTest {

    @Test
    public void supportedPlatformsMapToReleaseKeys() {
        assertEquals("darwin-arm64", Platform.key("Mac OS X", "aarch64"));
        assertEquals("linux-x64", Platform.key("Linux", "amd64"));
        assertEquals("win32-x64", Platform.key("Windows 11", "amd64"));
    }

    @Test
    public void unsupportedPlatformsAreNull() {
        assertNull(Platform.key("Mac OS X", "x86_64"));
        assertNull(Platform.key("Linux", "aarch64"));
        assertNull(Platform.key("FreeBSD", "amd64"));
        assertNull(Platform.key(null, null));
    }

    @Test
    public void windowsIsDetected() {
        assertTrue(Platform.isWindows("Windows Server 2022"));
    }

    @Test
    public void archiveNamesMatchTheReleaseFiles() {
        assertEquals("gnost-0.5.3-linux-x64.tar.gz", Platform.archiveName("0.5.3", "linux-x64"));
        assertEquals("gnost-0.5.3rc1-darwin-arm64.tar.gz", Platform.archiveName("0.5.3rc1", "darwin-arm64"));
        assertEquals("gnost-0.5.3-win32-x64.zip", Platform.archiveName("0.5.3", "win32-x64"));
    }
}
