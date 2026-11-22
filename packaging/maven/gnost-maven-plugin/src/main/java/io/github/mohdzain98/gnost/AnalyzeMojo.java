package io.github.mohdzain98.gnost;

import java.util.List;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;

/** Runs the quality analysis (gnost analyze): Python, JavaScript, TypeScript and Java. */
@Mojo(name = "analyze", requiresProject = false, aggregator = true, threadSafe = true)
public class AnalyzeMojo extends RepositoryMojo {

    /** Write the JSON and HTML report to .gnost/analysis/. */
    @Parameter(property = "gnost.out", defaultValue = "false")
    boolean out;

    /** Run analyzers in parallel. */
    @Parameter(property = "gnost.parallel", defaultValue = "false")
    boolean parallel;

    /** Comma-separated analyzer names; only these run. */
    @Parameter(property = "gnost.analyzer")
    String analyzer;

    /** Comma-separated languages to analyze: python, javascript, typescript, java (default: all). */
    @Parameter(property = "gnost.language")
    String language;

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

    /** Fail the build (exit code 3) when the final score (0 to 10) is below this. */
    @Parameter(property = "gnost.failUnder")
    Double failUnder;

    /** Report only findings that are not in this baseline file ("true" uses .gnost/baseline.json). */
    @Parameter(property = "gnost.baseline")
    String baseline;

    /** Save today's findings as the baseline ("true" uses .gnost/baseline.json). */
    @Parameter(property = "gnost.writeBaseline")
    String writeBaseline;

    /** With a baseline, fail the build when there are findings that are not in it. */
    @Parameter(property = "gnost.failOnNew", defaultValue = "false")
    boolean failOnNew;

    /** Write the findings as SARIF ("true" uses .gnost/analysis/analysis.sarif). */
    @Parameter(property = "gnost.sarif")
    String sarif;

    @Override
    String subcommand() {
        return "analyze";
    }

    @Override
    void addOptions(List<String> cmd) {
        super.addOptions(cmd);
        flag(cmd, out, "--out");
        flag(cmd, parallel, "--parallel");
        flag(cmd, quiet, "--quiet");
        flag(cmd, noProgress, "--no-progress");
        flag(cmd, compact, "--compact");
        flag(cmd, verbose, "-v");
        flag(cmd, listAnalyzers, "--list-analyzers");
        option(cmd, timeout, "--timeout");
        option(cmd, maxFindings, "--max-findings");
        option(cmd, failUnder, "--fail-under");
        optionalValue(cmd, baseline, "--baseline");
        optionalValue(cmd, writeBaseline, "--write-baseline");
        flag(cmd, failOnNew, "--fail-on-new");
        optionalValue(cmd, sarif, "--sarif");
        if (language != null) {
            for (String name : language.split(",")) {
                if (!name.trim().isEmpty()) {
                    option(cmd, name.trim(), "--language");
                }
            }
        }
        if (analyzer != null) {
            for (String name : analyzer.split(",")) {
                if (!name.trim().isEmpty()) {
                    option(cmd, name.trim(), "--analyzer");
                }
            }
        }
    }
}
