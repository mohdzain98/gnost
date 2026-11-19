package io.github.mohdzain98.gnost;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import com.sun.net.httpserver.HttpServer;
import java.io.File;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import org.junit.After;
import org.junit.Assume;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

public class ProvisionerTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    private final List<String> messages = new ArrayList<String>();
    private final Provisioner.Log log = new Provisioner.Log() {
        @Override
        public void info(String message) {
            messages.add(message);
        }
    };
    private HttpServer server;

    @Before
    public void setUp() {
        messages.clear();
    }

    @After
    public void tearDown() {
        if (server != null) {
            server.stop(0);
        }
    }

    /** A release folder with a fake archive for this platform; returns its folder. */
    private File release(String version, String key, boolean zip) throws Exception {
        File dir = tmp.newFolder("release-" + System.nanoTime());
        File src = tmp.newFolder("src-" + System.nanoTime());
        File bundle = new File(src, "gnost");
        assertTrue(bundle.mkdirs());
        File exe = new File(bundle, zip ? "gnost.exe" : "gnost");
        Files.write(exe.toPath(), "#!/bin/sh\necho 'gnost fake'\n".getBytes(StandardCharsets.UTF_8));
        assertTrue(exe.setExecutable(true));
        File archive = new File(dir, Platform.archiveName(version, key));
        if (zip) {
            try (ZipOutputStream z = new ZipOutputStream(Files.newOutputStream(archive.toPath()))) {
                z.putNextEntry(new ZipEntry("gnost/gnost.exe"));
                z.write(Files.readAllBytes(exe.toPath()));
                z.closeEntry();
            }
        } else {
            Process p = new ProcessBuilder("tar", "-czf", archive.getAbsolutePath(), "-C", src.getAbsolutePath(), "gnost")
                    .redirectErrorStream(true).start();
            assertTrue(p.waitFor(60, TimeUnit.SECONDS));
            assertEquals(0, p.exitValue());
        }
        return dir;
    }

    private static boolean hasTar() {
        try {
            Process p = new ProcessBuilder("tar", "--version").redirectErrorStream(true).start();
            p.getInputStream().close();
            return p.waitFor(20, TimeUnit.SECONDS);
        } catch (Exception e) {
            return false;
        }
    }

    private Provisioner provisioner(File home, String key, String url, String sha, boolean windows) {
        return new Provisioner(home, "0.5.3", key, url, sha, windows, null, log);
    }

    @Test
    public void downloadsVerifiesAndCaches() throws Exception {
        Assume.assumeTrue(hasTar() && !Platform.isWindows(System.getProperty("os.name")));
        File rel = release("0.5.3", "linux-x64", false);
        String sha = Downloader.sha256(new File(rel, "gnost-0.5.3-linux-x64.tar.gz"));
        File home = tmp.newFolder("home");
        Provisioner p = provisioner(home, "linux-x64", rel.toURI().toString(), sha, false);
        File exe = p.ensure();
        assertTrue(exe.isFile() && exe.canExecute());
        assertEquals(new File(new File(new File(home, "0.5.3"), "linux-x64"), "gnost"), exe.getParentFile());
        assertTrue(messages.get(0).startsWith("Downloading "));

        // The second call must not need the archive any more.
        assertTrue(new File(rel, "gnost-0.5.3-linux-x64.tar.gz").delete());
        messages.clear();
        assertEquals(exe, p.ensure());
        assertTrue(messages.isEmpty());
    }

    @Test
    public void aTamperedCacheIsFetchedAgain() throws Exception {
        Assume.assumeTrue(hasTar() && !Platform.isWindows(System.getProperty("os.name")));
        File rel = release("0.5.3", "linux-x64", false);
        String sha = Downloader.sha256(new File(rel, "gnost-0.5.3-linux-x64.tar.gz"));
        File home = tmp.newFolder("home");
        Provisioner p = provisioner(home, "linux-x64", rel.toURI().toString(), sha, false);
        File exe = p.ensure();
        Files.write(exe.toPath(), "evil".getBytes(StandardCharsets.UTF_8));
        messages.clear();
        File again = p.ensure();
        assertEquals("#!/bin/sh\necho 'gnost fake'\n", new String(Files.readAllBytes(again.toPath()), StandardCharsets.UTF_8));
        assertFalse(messages.isEmpty());
    }

    @Test
    public void windowsZipsAreUnpacked() throws Exception {
        File rel = release("0.5.3", "win32-x64", true);
        String sha = Downloader.sha256(new File(rel, "gnost-0.5.3-win32-x64.zip"));
        File home = tmp.newFolder("home");
        File exe = provisioner(home, "win32-x64", rel.toURI().toString(), sha, true).ensure();
        assertEquals("gnost.exe", exe.getName());
    }

    @Test
    public void aWrongChecksumIsRejectedAndNothingIsCached() throws Exception {
        File rel = release("0.5.3", "win32-x64", true);
        File home = tmp.newFolder("home");
        Provisioner p = provisioner(home, "win32-x64", rel.toURI().toString(),
                "0000000000000000000000000000000000000000000000000000000000000000", true);
        try {
            p.ensure();
            fail("expected a checksum failure");
        } catch (Provisioner.FetchException e) {
            assertTrue(e.getMessage(), e.getMessage().contains("checksum mismatch"));
        }
        assertFalse(p.cacheDir().exists());
        File[] left = new File(home, "0.5.3").listFiles();
        for (File f : left == null ? new File[0] : left) {
            assertFalse(f.getName(), f.getName().contains(".part-"));
        }
    }

    @Test
    public void aMissingChecksumMeansNoDownload() throws Exception {
        File home = tmp.newFolder("home");
        try {
            provisioner(home, "linux-x64", "file:///nowhere", null, false).ensure();
            fail("expected a refusal");
        } catch (Provisioner.FetchException e) {
            assertTrue(e.getMessage().contains("no checksum"));
        }
    }

    @Test
    public void httpDownloadsFollowRedirectsAndReportErrors() throws Exception {
        File rel = release("0.5.3", "win32-x64", true);
        final byte[] zip = Files.readAllBytes(new File(rel, "gnost-0.5.3-win32-x64.zip").toPath());
        String sha = Downloader.sha256(new File(rel, "gnost-0.5.3-win32-x64.zip"));
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/start/gnost-0.5.3-win32-x64.zip", ex -> {
            ex.getResponseHeaders().add("Location", "/real/file.zip");
            ex.sendResponseHeaders(302, -1);
            ex.close();
        });
        server.createContext("/real/file.zip", ex -> {
            ex.sendResponseHeaders(200, zip.length);
            try (OutputStream os = ex.getResponseBody()) {
                os.write(zip);
            }
        });
        server.start();
        String base = "http://127.0.0.1:" + server.getAddress().getPort();
        File home = tmp.newFolder("home");
        File exe = provisioner(home, "win32-x64", base + "/start", sha, true).ensure();
        assertTrue(exe.isFile());

        try {
            provisioner(tmp.newFolder("home2"), "win32-x64", base + "/nothing-here", sha, true).ensure();
            fail("expected a download failure");
        } catch (Provisioner.FetchException e) {
            assertTrue(e.getMessage(), e.getMessage().contains("HTTP 404"));
        }
    }

    @Test
    public void unreachableHostsGiveAClearError() throws Exception {
        try {
            provisioner(tmp.newFolder("home"), "win32-x64", "http://127.0.0.1:1", "ab", true).ensure();
            fail("expected a download failure");
        } catch (IOException e) {
            assertTrue(e.getMessage(), e.getMessage().contains("could not download"));
        }
    }
}
