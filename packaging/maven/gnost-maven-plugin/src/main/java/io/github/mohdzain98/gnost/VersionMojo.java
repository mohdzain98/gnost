package io.github.mohdzain98.gnost;

import java.util.List;
import org.apache.maven.plugins.annotations.Mojo;

/** Prints the gnost version that the plugin would run (gnost version). */
@Mojo(name = "version", requiresProject = false, aggregator = true, threadSafe = true)
public class VersionMojo extends AbstractGnostMojo {

    @Override
    String subcommand() {
        return "version";
    }

    @Override
    void addArguments(List<String> cmd) {
        // takes no folder
    }

    @Override
    void addOptions(List<String> cmd) {
        // no options
    }
}
