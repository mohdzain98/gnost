package io.github.mohdzain98.gnost;

import java.util.List;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;

/** Prints the language and size summary (gnost summary). */
@Mojo(name = "summary", requiresProject = false, aggregator = true, threadSafe = true)
public class SummaryMojo extends ScanMojo {

    /** Languages as GitHub's language bar shows them (bytes of committed files). */
    @Parameter(property = "gnost.git", defaultValue = "false")
    boolean git;

    @Override
    String subcommand() {
        return "summary";
    }

    @Override
    void addOptions(List<String> cmd) {
        super.addOptions(cmd);
        flag(cmd, git, "--git");
    }
}
