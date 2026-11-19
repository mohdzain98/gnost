package io.github.mohdzain98.gnost;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.Proxy;
import java.net.URL;
import java.net.URLConnection;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/** Downloads one file over http, https or file URLs and computes SHA-256 sums. */
final class Downloader {

    private static final int CONNECT_TIMEOUT_MS = 20000;
    private static final int READ_TIMEOUT_MS = 120000;

    private Downloader() {
    }

    /** Download url to out and return the number of bytes written. Follows redirects. */
    static long download(String url, File out, Proxy proxy) throws IOException {
        URL current = new URL(url);
        for (int hops = 0; hops < 8; hops++) {
            URLConnection c = proxy != null ? current.openConnection(proxy) : current.openConnection();
            c.setConnectTimeout(CONNECT_TIMEOUT_MS);
            c.setReadTimeout(READ_TIMEOUT_MS);
            if (c instanceof HttpURLConnection) {
                HttpURLConnection h = (HttpURLConnection) c;
                h.setInstanceFollowRedirects(false);
                h.setRequestProperty("User-Agent", "gnost-maven-plugin");
                int code = h.getResponseCode();
                if (code == 301 || code == 302 || code == 303 || code == 307 || code == 308) {
                    String next = h.getHeaderField("Location");
                    h.disconnect();
                    if (next == null) {
                        throw new IOException("redirect without a location from " + current);
                    }
                    current = new URL(current, next);
                    continue;
                }
                if (code != 200) {
                    h.disconnect();
                    throw new IOException("HTTP " + code + " from " + current);
                }
            }
            return copy(c, out);
        }
        throw new IOException("too many redirects from " + url);
    }

    private static long copy(URLConnection c, File out) throws IOException {
        long total = 0;
        try (InputStream in = c.getInputStream(); OutputStream os = Files.newOutputStream(out.toPath())) {
            byte[] buf = new byte[65536];
            int n;
            while ((n = in.read(buf)) > 0) {
                os.write(buf, 0, n);
                total += n;
            }
        }
        return total;
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
}
