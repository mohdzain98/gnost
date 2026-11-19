package io.github.mohdzain98.gnost;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.net.Proxy;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;

/**
 * Makes sure the GNOST executable for one release and platform is in the cache
 * (home/RELEASE/KEY), downloading and checking it if it is not.
 */
final class Provisioner {

    /** Receives progress messages. */
    interface Log {
        void info(String message);
    }

    /** The download or the unpacking failed; the message says why. */
    static final class FetchException extends IOException {
        FetchException(String message, Throwable cause) {
            super(message, cause);
        }

        FetchException(String message) {
            super(message);
        }
    }

    private final File home;
    private final String release;
    private final String key;
    private final String baseUrl;
    private final String expectedSha;
    private final boolean windows;
    private final Proxy proxy;
    private final Log log;

    Provisioner(File home, String release, String key, String baseUrl, String expectedSha,
            boolean windows, Proxy proxy, Log log) {
        this.home = home;
        this.release = release;
        this.key = key;
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.expectedSha = expectedSha;
        this.windows = windows;
        this.proxy = proxy;
        this.log = log;
    }

    /** The cache folder used for this release and platform. */
    File cacheDir() {
        return new File(new File(home, release), key);
    }

    /** The URL the archive is downloaded from. */
    String url() {
        return baseUrl + "/" + Platform.archiveName(release, key);
    }

    /** The executable, downloading it first if the cache has no valid copy. */
    File ensure() throws IOException {
        if (expectedSha == null) {
            throw new FetchException("this plugin build has no checksum for " + key
                    + ", so it will not download a binary");
        }
        File exe = cached();
        if (exe != null) {
            return exe;
        }
        File parent = cacheDir().getParentFile();
        if (!parent.isDirectory() && !parent.mkdirs()) {
            throw new FetchException("cannot create the cache folder " + parent);
        }
        File lockFile = new File(parent, key + ".lock");
        try (RandomAccessFile raf = new RandomAccessFile(lockFile, "rw");
                FileChannel ch = raf.getChannel();
                FileLock ignored = ch.lock()) {
            exe = cached();
            if (exe != null) {
                return exe;
            }
            return install();
        }
    }

    /** The executable if the cache holds an intact copy of this release, else null. */
    private File cached() throws IOException {
        File dir = cacheDir();
        File exe = executable(dir);
        File marker = new File(dir, "installed.txt");
        if (!exe.isFile() || !marker.isFile()) {
            return null;
        }
        String[] parts = new String(Files.readAllBytes(marker.toPath()), StandardCharsets.UTF_8).trim().split("\\s+");
        if (parts.length != 2 || !parts[0].equals(expectedSha) || !parts[1].equals(Downloader.sha256(exe))) {
            return null;
        }
        return exe;
    }

    private File executable(File dir) {
        return new File(new File(dir, "gnost"), windows ? "gnost.exe" : "gnost");
    }

    private File install() throws IOException {
        File parent = cacheDir().getParentFile();
        File work = new File(parent, key + ".part-" + System.nanoTime());
        File archive = new File(work, Platform.archiveName(release, key));
        File unpacked = new File(work, "unpacked");
        try {
            if (!work.mkdirs()) {
                throw new FetchException("cannot create " + work);
            }
            String url = url();
            log.info("Downloading " + url);
            long bytes;
            try {
                bytes = Downloader.download(url, archive, proxy);
            } catch (IOException e) {
                throw new FetchException("could not download " + url + ": " + e.getMessage(), e);
            }
            String actual = Downloader.sha256(archive);
            if (!actual.equals(expectedSha)) {
                throw new FetchException("checksum mismatch for " + url + " (expected " + expectedSha
                        + ", got " + actual + "); the file was discarded");
            }
            log.info("Downloaded " + (bytes / 1000000) + " MB, checksum verified");
            try {
                Archives.extract(archive, unpacked, windows);
            } catch (IOException e) {
                throw new FetchException("could not unpack " + archive.getName() + ": " + e.getMessage(), e);
            }
            File exe = new File(new File(unpacked, "gnost"), windows ? "gnost.exe" : "gnost");
            if (!exe.isFile()) {
                throw new FetchException("the archive does not contain gnost/" + exe.getName());
            }
            if (!exe.canExecute() && !exe.setExecutable(true)) {
                throw new FetchException("cannot make " + exe + " executable");
            }
            Files.write(new File(unpacked, "installed.txt").toPath(),
                    (expectedSha + " " + Downloader.sha256(exe) + "\n").getBytes(StandardCharsets.UTF_8));
            deleteTree(cacheDir());
            Files.move(unpacked.toPath(), cacheDir().toPath(), StandardCopyOption.ATOMIC_MOVE);
            return executable(cacheDir());
        } finally {
            deleteTree(work);
        }
    }

    static void deleteTree(File f) {
        File[] kids = f.listFiles();
        if (kids != null) {
            for (File k : kids) {
                if (!Files.isSymbolicLink(k.toPath())) {
                    deleteTree(k);
                } else {
                    k.delete();
                }
            }
        }
        f.delete();
    }
}
