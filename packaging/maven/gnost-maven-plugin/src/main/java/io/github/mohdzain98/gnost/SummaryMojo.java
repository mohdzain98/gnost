package io.github.mohdzain98.gnost;

import java.util.List;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;

/** Prints the language and size summary (gnost summary). */
@Mojo(name = "summary", requiresProject = false, aggregator = true, threadSafe = true)
public class SummaryMojo extends AbstractGnostMojo {

    /** Comma-separated folder names to skip. */
    @Parameter(property = "gnost.exclude")
    String exclude;

    /** Comma-separated folder names to scan (only these). */
    @Parameter(property = "gnost.include")
    String include;

    /** Show a progress bar. */
    @Parameter(property = "gnost.progress", defaultValue = "false")
    boolean progress;

    @Override
    String subcommand() {
        return "summary";
    }

    @Override
    void addOptions(List<String> cmd) {
        option(cmd, exclude, "--exclude");
        option(cmd, include, "--include");
        flag(cmd, progress, "--progress");
    }
}
