package io.github.mohdzain98.gnost;

import java.util.List;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;

/** Runs the quality analysis (gnost analyze). Python code only. */
@Mojo(name = "analyze", requiresProject = false, aggregator = true, threadSafe = true)
public class AnalyzeMojo extends AbstractGnostMojo {

    /** Write the JSON and HTML report to docs/analysis/. */
    @Parameter(property = "gnost.out", defaultValue = "false")
    boolean out;

    /** Run analyzers in parallel. */
    @Parameter(property = "gnost.parallel", defaultValue = "false")
    boolean parallel;

    /** Comma-separated analyzer names; only these run. */
    @Parameter(property = "gnost.analyzer")
    String analyzer;

    /** Hide info logs. */
    @Parameter(property = "gnost.quiet", defaultValue = "false")
    boolean quiet;

    /** Hide progress updates. */
    @Parameter(property = "gnost.noProgress", defaultValue = "false")
    boolean noProgress;

    /** Write compact JSON. */
    @Parameter(property = "gnost.compact", defaultValue = "false")
    boolean compact;

    /** Show tracebacks for errors. */
    @Parameter(property = "gnost.verbose", defaultValue = "false")
    boolean verbose;

    /** List the available analyzers and exit. */
    @Parameter(property = "gnost.listAnalyzers", defaultValue = "false")
    boolean listAnalyzers;

    /** Seconds to wait before giving up. */
    @Parameter(property = "gnost.timeout")
    Integer timeout;

    /** Finding limit per analyzer. */
    @Parameter(property = "gnost.maxFindings")
    Integer maxFindings;

    @Override
    String subcommand() {
        return "analyze";
    }

    @Override
    void addOptions(List<String> cmd) {
        flag(cmd, out, "--out");
        flag(cmd, parallel, "--parallel");
        flag(cmd, quiet, "--quiet");
        flag(cmd, noProgress, "--no-progress");
        flag(cmd, compact, "--compact");
        flag(cmd, verbose, "-v");
        flag(cmd, listAnalyzers, "--list-analyzers");
        option(cmd, timeout, "--timeout");
        option(cmd, maxFindings, "--max-findings");
        if (analyzer != null) {
            for (String name : analyzer.split(",")) {
                if (!name.trim().isEmpty()) {
                    option(cmd, name.trim(), "--analyzer");
                }
            }
        }
    }
}
