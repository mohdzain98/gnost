package io.github.mohdzain98.gnost;

import java.util.List;
import org.apache.maven.plugins.annotations.Parameter;

/** Base for the goals that count files and lines (summary, stats, folders, files). */
public abstract class ScanMojo extends AbstractGnostMojo {

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
    void addOptions(List<String> cmd) {
        option(cmd, exclude, "--exclude");
        option(cmd, include, "--include");
        flag(cmd, progress, "--progress");
    }
}
