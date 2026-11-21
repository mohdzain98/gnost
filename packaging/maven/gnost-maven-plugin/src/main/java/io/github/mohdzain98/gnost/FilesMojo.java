package io.github.mohdzain98.gnost;

import java.util.List;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;

/** Prints the largest files (gnost files). */
@Mojo(name = "files", requiresProject = false, aggregator = true, threadSafe = true)
public class FilesMojo extends ScanMojo {

    /** How many files to show. */
    @Parameter(property = "gnost.top")
    Integer top;

    @Override
    String subcommand() {
        return "files";
    }

    @Override
    void addOptions(List<String> cmd) {
        super.addOptions(cmd);
        option(cmd, top, "--top");
    }
}
