package io.github.mohdzain98.gnost;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.TimeUnit;

/** Finds a gnost that is already installed (pip, pipx, npm) and asks it for its version. */
final class PathFinder {

    private PathFinder() {
    }

    /** The first gnost executable on the given PATH value, or null. */
    static File find(String pathEnv, boolean windows) {
        if (pathEnv == null || pathEnv.isEmpty()) {
            return null;
        }
        String[] names = windows
                ? new String[] {"gnost.exe", "gnost.cmd", "gnost.bat"}
                : new String[] {"gnost"};
        for (String dir : pathEnv.split(File.pathSeparator)) {
            if (dir.isEmpty()) {
                continue;
            }
            for (String name : names) {
                File f = new File(dir, name);
                if (f.isFile() && (windows || f.canExecute())) {
                    return f;
                }
            }
        }
        return null;
    }

    /** The version printed by "gnost version" ("gnost 0.5.3" gives "0.5.3"), or null if it fails. */
    static String versionOf(File exe) {
        try {
            Process p = new ProcessBuilder(exe.getAbsolutePath(), "version").redirectErrorStream(true).start();
            StringBuilder out = new StringBuilder();
            try (InputStream in = p.getInputStream()) {
                byte[] buf = new byte[512];
                int n;
                while ((n = in.read(buf)) > 0 && out.length() < 1000) {
                    out.append(new String(buf, 0, n));
                }
            }
            if (!p.waitFor(30, TimeUnit.SECONDS)) {
                p.destroyForcibly();
                return null;
            }
            return parseVersion(out.toString());
        } catch (IOException e) {
            return null;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return null;
        }
    }

    static String parseVersion(String output) {
        String[] lines = output == null ? new String[0] : output.trim().split("\\r?\\n");
        for (String line : lines) {
            String t = line.trim();
            if (t.startsWith("gnost ")) {
                return t.substring("gnost ".length()).trim();
            }
        }
        return null;
    }
}
