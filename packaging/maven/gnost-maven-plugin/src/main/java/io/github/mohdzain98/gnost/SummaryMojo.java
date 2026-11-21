package io.github.mohdzain98.gnost;

import org.apache.maven.plugins.annotations.Mojo;

/** Prints the language and size summary (gnost summary). */
@Mojo(name = "summary", requiresProject = false, aggregator = true, threadSafe = true)
public class SummaryMojo extends ScanMojo {

    @Override
    String subcommand() {
        return "summary";
    }
}
