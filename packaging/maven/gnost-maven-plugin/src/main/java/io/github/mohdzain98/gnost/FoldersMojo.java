package io.github.mohdzain98.gnost;

import org.apache.maven.plugins.annotations.Mojo;

/** Prints lines of code grouped by folder (gnost folders). */
@Mojo(name = "folders", requiresProject = false, aggregator = true, threadSafe = true)
public class FoldersMojo extends ScanMojo {

    @Override
    String subcommand() {
        return "folders";
    }
}
