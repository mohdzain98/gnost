package io.github.mohdzain98.gnost;

import java.io.File;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Notes which of the files GNOST writes (ONBOARD.md, docs/...) were created or changed by a run. */
final class OutputWatcher {

    static final String[] LOCATIONS = {"ONBOARD.md", "docs/flow", "docs/insights", "docs/analysis"};

    private final List<File> roots;
    private Map<String, String> before = new LinkedHashMap<String, String>();
    private long started;

    /** Watch the folder GNOST will scan and the repository root above it (where it writes). */
    OutputWatcher(File target) {
        Set<File> found = new LinkedHashSet<File>();
        File abs = target.getAbsoluteFile().toPath().normalize().toFile();
        File dir = abs.isFile() ? abs.getParentFile() : abs;
        found.add(dir);
        found.add(repoRoot(dir));
        roots = new ArrayList<File>(found);
    }

    static File repoRoot(File start) {
        for (File d = start; d != null; d = d.getParentFile()) {
            if (new File(d, ".git").exists() || new File(d, "pyproject.toml").isFile()) {
                return d;
            }
        }
        return start;
    }

    void snapshot() {
        started = System.currentTimeMillis();
        before = scan();
    }

    /** One line per output location that is new or changed since snapshot(). */
    List<String> changes() {
        Map<String, String> after = scan();
        Map<String, Integer> counts = new LinkedHashMap<String, Integer>();
        for (Map.Entry<String, String> e : after.entrySet()) {
            String old = before.get(e.getKey());
            File f = new File(e.getKey());
            boolean touched = f.lastModified() >= started - 2000;
            if (old == null || !old.equals(e.getValue()) || touched) {
                String loc = location(e.getKey());
                counts.put(loc, counts.containsKey(loc) ? counts.get(loc) + 1 : 1);
            }
        }
        List<String> lines = new ArrayList<String>();
        for (Map.Entry<String, Integer> e : counts.entrySet()) {
            File f = new File(e.getKey());
            lines.add(f.isDirectory() ? e.getKey() + " (" + e.getValue() + " files)" : e.getKey());
        }
        return lines;
    }

    private String location(String file) {
        for (File root : roots) {
            for (String loc : LOCATIONS) {
                File l = new File(root, loc);
                if (file.equals(l.getPath()) || file.startsWith(l.getPath() + File.separator)) {
                    return l.getPath();
                }
            }
        }
        return file;
    }

    private Map<String, String> scan() {
        Map<String, String> files = new LinkedHashMap<String, String>();
        for (File root : roots) {
            for (String loc : LOCATIONS) {
                walk(new File(root, loc), files);
            }
        }
        return files;
    }

    private static void walk(File f, Map<String, String> out) {
        if (f.isFile()) {
            out.put(f.getPath(), f.lastModified() + ":" + f.length());
        } else if (f.isDirectory()) {
            File[] kids = f.listFiles();
            if (kids != null) {
                for (File k : kids) {
                    walk(k, out);
                }
            }
        }
    }
}
