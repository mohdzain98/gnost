package io.github.mohdzain98.gnost;

import java.io.File;
import java.util.List;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;

/** Opens the analysis report, the flow explorer or a file in the browser (gnost open). */
@Mojo(name = "open", requiresProject = false, aggregator = true, threadSafe = true)
public class OpenMojo extends AbstractGnostMojo {

    /** What to open: report (default), flow, or the path of a .mmd, .md or .html file. */
    @Parameter(property = "gnost.target", defaultValue = "report")
    String target;

    /** Set to false (-Dgnost.open=false) to write the page but not start a browser, for CI. */
    @Parameter(property = "gnost.open", defaultValue = "true")
    boolean open;

    /** Where to save the HTML page. */
    @Parameter(property = "gnost.output")
    File output;

    /** Custom report or diagram path. */
    @Parameter(property = "gnost.file")
    File file;

    /** auto, graph or mermaid. */
    @Parameter(property = "gnost.view")
    String view;

    @Override
    String subcommand() {
        return "open";
    }

    @Override
    void addArguments(List<String> cmd) {
        cmd.add(target == null || target.isEmpty() ? "report" : target);
    }

    @Override
    void addOptions(List<String> cmd) {
        flag(cmd, !open, "--no-open");
        option(cmd, file, "--path");
        option(cmd, output, "--output");
        option(cmd, view, "--view");
    }
}
