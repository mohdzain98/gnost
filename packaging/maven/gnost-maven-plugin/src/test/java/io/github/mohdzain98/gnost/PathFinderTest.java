package io.github.mohdzain98.gnost;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import org.junit.Assume;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

public class PathFinderTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    private File fakeGnost(File dir, String printed) throws Exception {
        File exe = new File(dir, "gnost");
        Files.write(exe.toPath(), ("#!/bin/sh\necho '" + printed + "'\n").getBytes(StandardCharsets.UTF_8));
        exe.setExecutable(true);
        return exe;
    }

    @Test
    public void findsTheFirstGnostOnPath() throws Exception {
        Assume.assumeFalse(Platform.isWindows(System.getProperty("os.name")));
        File a = tmp.newFolder("a");
        File b = tmp.newFolder("b");
        File first = fakeGnost(a, "gnost 1.0.0");
        fakeGnost(b, "gnost 2.0.0");
        String path = tmp.getRoot() + File.separator + "missing" + File.pathSeparator + a + File.pathSeparator + b;
        assertEquals(first, PathFinder.find(path, false));
    }

    @Test
    public void nothingOnPathGivesNull() {
        assertNull(PathFinder.find(null, false));
        assertNull(PathFinder.find("", false));
        assertNull(PathFinder.find(tmp.getRoot().getPath(), false));
    }

    @Test
    public void readsTheVersionFromGnostVersion() throws Exception {
        Assume.assumeFalse(Platform.isWindows(System.getProperty("os.name")));
        File exe = fakeGnost(tmp.newFolder("c"), "gnost 0.5.3");
        assertEquals("0.5.3", PathFinder.versionOf(exe));
    }

    @Test
    public void parsesVersionOutput() {
        assertEquals("0.5.3rc1", PathFinder.parseVersion("gnost 0.5.3rc1\n"));
        assertEquals("0.4.0", PathFinder.parseVersion("warning\r\ngnost 0.4.0\r\n"));
        assertNull(PathFinder.parseVersion("something else"));
        assertNull(PathFinder.parseVersion(null));
    }
}
