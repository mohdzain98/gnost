package io.github.mohdzain98.gnost;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import org.junit.Test;

public class MojoCommandTest {

    @Test
    public void onboardBuildsFlagsInOrder() {
        OnboardMojo m = new OnboardMojo();
        m.path = "src";
        m.mermaid = true;
        m.depth = 2;
        m.json = "true";
        m.args = "--progress  --layered";
        assertEquals(
                Arrays.asList("gnost", "onboard", "src", "--mermaid", "--depth", "2", "--json", "--progress", "--layered"),
                m.command("gnost"));
    }

    @Test
    public void onboardJsonFileIsPassedThrough() {
        OnboardMojo m = new OnboardMojo();
        m.json = "out.json";
        assertEquals(Arrays.asList("g", "onboard", ".", "--json", "out.json"), m.command("g"));
    }

    @Test
    public void analyzeRepeatsAnalyzerOption() {
        AnalyzeMojo m = new AnalyzeMojo();
        m.out = true;
        m.analyzer = "radon, bandit";
        m.timeout = 60;
        assertEquals(
                Arrays.asList("g", "analyze", ".", "--out", "--timeout", "60", "--analyzer", "radon", "--analyzer", "bandit"),
                m.command("g"));
    }

    @Test
    public void summaryUsesIncludeAndExclude() {
        SummaryMojo m = new SummaryMojo();
        m.exclude = "build,out";
        assertEquals(Arrays.asList("g", "summary", ".", "--exclude", "build,out"), m.command("g"));
    }

    @Test
    public void failureMessageSuggestsInstallingGnostOnPath() {
        String m = AbstractGnostMojo.failureMessage("HTTP 403 from x", "https://example.org/g.tar.gz");
        assertTrue(m, m.contains("pipx install gnost"));
        assertTrue(m, m.contains("npm install --global gnost-cli"));
        assertTrue(m, m.contains("Maven Central"));
        assertTrue(m, m.contains("https://example.org/g.tar.gz"));
    }

    @Test
    public void spacesInArgumentsAreQuotedForDisplay() {
        assertEquals(Arrays.asList("g", "\"my dir\"", "x"), AbstractGnostMojo.quoted(Arrays.asList("g", "my dir", "x")));
    }
}
