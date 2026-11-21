package io.github.mohdzain98.gnost;

import org.apache.maven.plugins.annotations.Mojo;

/** Prints detailed statistics per language (gnost stats). */
@Mojo(name = "stats", requiresProject = false, aggregator = true, threadSafe = true)
public class StatsMojo extends ScanMojo {

    @Override
    String subcommand() {
        return "stats";
    }
}
