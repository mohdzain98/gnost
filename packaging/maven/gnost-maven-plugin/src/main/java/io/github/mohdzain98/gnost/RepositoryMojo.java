package io.github.mohdzain98.gnost;

import java.util.List;
import org.apache.maven.plugins.annotations.Parameter;

/** Base for the goals that also accept a repository address as the path (onboard, analyze, changes). */
public abstract class RepositoryMojo extends AbstractGnostMojo {

    /** For a repository address: the branch or tag to clone. */
    @Parameter(property = "gnost.ref")
    String ref;

    @Override
    void addOptions(List<String> cmd) {
        option(cmd, ref, "--ref");
    }
}
