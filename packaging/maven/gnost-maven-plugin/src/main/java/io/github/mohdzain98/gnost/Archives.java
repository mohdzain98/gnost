package io.github.mohdzain98.gnost;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.util.Enumeration;
import java.util.concurrent.TimeUnit;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/** Unpacks a GNOST release archive: zip on Windows, tar.gz (through the system tar) elsewhere. */
final class Archives {

    private Archives() {
    }

    static void extract(File archive, File dest, boolean zip) throws IOException {
        if (!dest.isDirectory() && !dest.mkdirs()) {
            throw new IOException("cannot create " + dest);
        }
        if (zip) {
            unzip(archive, dest);
        } else {
            untar(archive, dest);
        }
    }

    private static void untar(File archive, File dest) throws IOException {
        Process p;
        try {
            p = new ProcessBuilder("tar", "-xzf", archive.getAbsolutePath(), "-C", dest.getAbsolutePath())
                    .redirectErrorStream(true)
                    .start();
        } catch (IOException e) {
            throw new IOException("the 'tar' command is needed to unpack gnost but could not be started: "
                    + e.getMessage(), e);
        }
        StringBuilder out = new StringBuilder();
        try (InputStream in = p.getInputStream()) {
            byte[] buf = new byte[4096];
            int n;
            while ((n = in.read(buf)) > 0 && out.length() < 2000) {
                out.append(new String(buf, 0, n));
            }
        }
        try {
            if (!p.waitFor(300, TimeUnit.SECONDS)) {
                p.destroyForcibly();
                throw new IOException("tar took too long to unpack " + archive);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("interrupted while unpacking " + archive, e);
        }
        if (p.exitValue() != 0) {
            throw new IOException("tar could not unpack " + archive + ": " + out.toString().trim());
        }
    }

    private static void unzip(File zip, File dest) throws IOException {
        String root = dest.getCanonicalPath() + File.separator;
        try (ZipFile z = new ZipFile(zip)) {
            Enumeration<? extends ZipEntry> entries = z.entries();
            while (entries.hasMoreElements()) {
                ZipEntry e = entries.nextElement();
                File out = new File(dest, e.getName());
                if (!out.getCanonicalPath().startsWith(root)) {
                    throw new IOException("unsafe path in archive: " + e.getName());
                }
                if (e.isDirectory()) {
                    out.mkdirs();
                    continue;
                }
                out.getParentFile().mkdirs();
                try (InputStream in = z.getInputStream(e); OutputStream os = Files.newOutputStream(out.toPath())) {
                    byte[] buf = new byte[65536];
                    int n;
                    while ((n = in.read(buf)) > 0) {
                        os.write(buf, 0, n);
                    }
                }
            }
        }
    }
}
