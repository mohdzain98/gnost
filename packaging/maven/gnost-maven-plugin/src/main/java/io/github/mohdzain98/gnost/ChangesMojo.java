package io.github.mohdzain98.gnost;

import java.util.List;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;

/** Shows what a change touches: files, blast radius, risk, routes, cycles (gnost changes). */
@Mojo(name = "changes", requiresProject = false, aggregator = true, threadSafe = true)
public class ChangesMojo extends RepositoryMojo {

    /** BASE or BASE..HEAD, for example origin/main. Required. */
    @Parameter(property = "gnost.refs", required = true)
    String refs;

    /** How far to follow importers. */
    @Parameter(property = "gnost.depth")
    Integer depth;

    /** What to print: text, markdown or json. */
    @Parameter(property = "gnost.format")
    String format;

    /** Also run the analyzers on the changed Python files. */
    @Parameter(property = "gnost.findings", defaultValue = "false")
    boolean findings;

    /** Skip scanning the base commit. */
    @Parameter(property = "gnost.noCycles", defaultValue = "false")
    boolean noCycles;

    /** Fail the build (exit code 3) when the change breaks an [architecture] rule. */
    @Parameter(property = "gnost.failOnViolations", defaultValue = "false")
    boolean failOnViolations;

    /** Do not write .gnost/changes/. */
    @Parameter(property = "gnost.noWrite", defaultValue = "false")
    boolean noWrite;

    @Override
    String subcommand() {
        return "changes";
    }

    @Override
    void addArguments(List<String> cmd) {
        cmd.add(refs);
        super.addArguments(cmd);
    }

    @Override
    void addOptions(List<String> cmd) {
        super.addOptions(cmd);
        option(cmd, depth, "--depth");
        option(cmd, format, "--format");
        flag(cmd, findings, "--findings");
        flag(cmd, noCycles, "--no-cycles");
        flag(cmd, noWrite, "--no-write");
        flag(cmd, failOnViolations, "--fail-on-violations");
    }
}
