package io.github.mohdzain98.gnost;

import java.util.List;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;

/** Writes .gnost.toml and can wire GNOST into the build (gnost init). */
@Mojo(name = "init", requiresProject = false, aggregator = true, threadSafe = true)
public class InitMojo extends AbstractGnostMojo {

    /** Overwrite files that already exist. */
    @Parameter(property = "gnost.force", defaultValue = "false")
    boolean force;

    /** Print the default settings instead of writing the file. */
    @Parameter(property = "gnost.print", defaultValue = "false")
    boolean print;

    /** Show what would change and write nothing. */
    @Parameter(property = "gnost.dryRun", defaultValue = "false")
    boolean dryRun;

    /** Add gnost-maven-plugin to pom.xml. */
    @Parameter(property = "gnost.pom", defaultValue = "false")
    boolean pom;

    /** Add a gnost script to package.json. */
    @Parameter(property = "gnost.npm", defaultValue = "false")
    boolean npm;

    /** Write .github/workflows/gnost.yml. */
    @Parameter(property = "gnost.githubAction", defaultValue = "false")
    boolean githubAction;

    /** With githubAction: also write .github/workflows/gnost-comment.yml (comments on pull requests from forks). */
    @Parameter(property = "gnost.forkComments", defaultValue = "false")
    boolean forkComments;

    /** Write AGENTS.md that points coding agents to the .gnost/ folder. */
    @Parameter(property = "gnost.agents", defaultValue = "false")
    boolean agents;

    @Override
    String subcommand() {
        return "init";
    }

    @Override
    void addOptions(List<String> cmd) {
        flag(cmd, force, "--force");
        flag(cmd, print, "--print");
        flag(cmd, dryRun, "--dry-run");
        flag(cmd, pom, "--pom");
        flag(cmd, npm, "--npm");
        flag(cmd, githubAction, "--github-action");
        flag(cmd, forkComments, "--fork-comments");
        flag(cmd, agents, "--agents");
    }
}
