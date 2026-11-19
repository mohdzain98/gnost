package io.github.mohdzain98.gnost;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.List;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

public class OutputWatcherTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @Test
    public void reportsNewFilesAndFolders() throws Exception {
        File project = tmp.newFolder("proj");
        OutputWatcher w = new OutputWatcher(project);
        w.snapshot();
        Files.write(new File(project, "ONBOARD.md").toPath(), "x".getBytes(StandardCharsets.UTF_8));
        File flow = new File(project, "docs/flow");
        assertTrue(flow.mkdirs());
        Files.write(new File(flow, "a.mmd").toPath(), "a".getBytes(StandardCharsets.UTF_8));
        Files.write(new File(flow, "b.mmd").toPath(), "b".getBytes(StandardCharsets.UTF_8));
        List<String> changes = w.changes();
        assertEquals(2, changes.size());
        assertEquals(new File(project, "ONBOARD.md").getPath(), changes.get(0));
        assertEquals(new File(project, "docs/flow").getPath() + " (2 files)", changes.get(1));
    }

    @Test
    public void nothingWrittenMeansNoChanges() throws Exception {
        File project = tmp.newFolder("empty");
        OutputWatcher w = new OutputWatcher(project);
        w.snapshot();
        assertTrue(w.changes().isEmpty());
    }

    @Test
    public void watchesTheRepositoryRootAboveTheScannedFolder() throws Exception {
        File repo = tmp.newFolder("repo");
        assertTrue(new File(repo, ".git").mkdirs());
        File sub = new File(repo, "app/src");
        assertTrue(sub.mkdirs());
        OutputWatcher w = new OutputWatcher(sub);
        w.snapshot();
        Files.write(new File(repo, "ONBOARD.md").toPath(), "x".getBytes(StandardCharsets.UTF_8));
        assertEquals(1, w.changes().size());
    }
}
