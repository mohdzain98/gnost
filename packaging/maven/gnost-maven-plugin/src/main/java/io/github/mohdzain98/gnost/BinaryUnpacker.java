package io.github.mohdzain98.gnost;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Enumeration;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/** Unpacks a GNOST binary zip next to itself and checks the executable's SHA-256. */
final class BinaryUnpacker {

    private static final String MARKER = ".unpacked";

    private BinaryUnpacker() {
    }

    /** Unpack zip once (re-unpacking if it changed), verify, and return the executable. */
    static File prepare(File zip, boolean windows) throws IOException {
        File dir = new File(zip.getParentFile(), "unpacked");
        File marker = new File(dir, MARKER);
        String stamp = zip.length() + ":" + zip.lastModified();
        if (!marker.isFile() || !stamp.equals(read(marker))) {
            deleteTree(dir);
            unzip(zip, dir);
            Files.write(marker.toPath(), stamp.getBytes(StandardCharsets.UTF_8));
        }
        File bundle = new File(dir, "gnost");
        File exe = new File(bundle, windows ? "gnost.exe" : "gnost");
        verify(exe, new File(bundle, "gnost.sha256"));
        if (!exe.canExecute() && !exe.setExecutable(true)) {
            throw new IOException("cannot make " + exe + " executable");
        }
        return exe;
    }

    static void unzip(File zip, File dest) throws IOException {
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

    /** Fail unless the executable's SHA-256 equals the first word of the checksum file. */
    static void verify(File exe, File sums) throws IOException {
        if (!exe.isFile() || !sums.isFile()) {
            throw new IOException("incomplete GNOST binary in " + exe.getParent());
        }
        String expected = read(sums).trim().split("\\s+")[0].toLowerCase();
        String actual = sha256(exe);
        if (!actual.equals(expected)) {
            throw new IOException("checksum mismatch for " + exe + " (expected " + expected + ", got " + actual + ")");
        }
    }

    static String sha256(File file) throws IOException {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            try (InputStream in = Files.newInputStream(file.toPath())) {
                byte[] buf = new byte[65536];
                int n;
                while ((n = in.read(buf)) > 0) {
                    md.update(buf, 0, n);
                }
            }
            StringBuilder hex = new StringBuilder();
            for (byte b : md.digest()) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IOException(e);
        }
    }

    private static String read(File f) throws IOException {
        return new String(Files.readAllBytes(f.toPath()), StandardCharsets.UTF_8);
    }

    private static void deleteTree(File f) {
        File[] kids = f.listFiles();
        if (kids != null) {
            for (File k : kids) {
                deleteTree(k);
            }
        }
        f.delete();
    }
}
