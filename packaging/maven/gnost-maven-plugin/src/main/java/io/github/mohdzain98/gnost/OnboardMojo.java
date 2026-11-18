package io.github.mohdzain98.gnost;

import java.util.List;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;

/** Writes onboarding docs and flow diagrams (gnost onboard). Output goes in docs/. */
@Mojo(name = "onboard", requiresProject = false, aggregator = true, threadSafe = true)
public class OnboardMojo extends AbstractGnostMojo {

    /** Write only the Mermaid flow diagram. */
    @Parameter(property = "gnost.mermaid", defaultValue = "false")
    boolean mermaid;

    /** Draw the diagram as Entry, Core and Leaf layers. */
    @Parameter(property = "gnost.layered", defaultValue = "false")
    boolean layered;

    /** Add an onboarding link to README.md. */
    @Parameter(property = "gnost.inject", defaultValue = "false")
    boolean inject;

    /** Show a progress bar. */
    @Parameter(property = "gnost.progress", defaultValue = "false")
    boolean progress;

    /** Write only the insights JSON. */
    @Parameter(property = "gnost.insightsOnly", defaultValue = "false")
    boolean insightsOnly;

    /** Limit the flow depth. */
    @Parameter(property = "gnost.depth")
    Integer depth;

    /** Largest diagram to draw file by file. */
    @Parameter(property = "gnost.maxEdges")
    Integer maxEdges;

    /** Group diagrams by folder, this many levels deep. */
    @Parameter(property = "gnost.collapse")
    Integer collapse;

    /** Also write insights JSON: "true" for the default file, or a file name. */
    @Parameter(property = "gnost.json")
    String json;

    @Override
    String subcommand() {
        return "onboard";
    }

    @Override
    void addOptions(List<String> cmd) {
        flag(cmd, mermaid, "--mermaid");
        flag(cmd, layered, "--layered");
        flag(cmd, inject, "--inject");
        flag(cmd, progress, "--progress");
        flag(cmd, insightsOnly, "--insights-only");
        option(cmd, depth, "--depth");
        option(cmd, maxEdges, "--max-edges");
        option(cmd, collapse, "--collapse");
        if (json != null) {
            cmd.add("--json");
            if (!json.isEmpty() && !"true".equalsIgnoreCase(json)) {
                cmd.add(json);
            }
        }
    }
}
