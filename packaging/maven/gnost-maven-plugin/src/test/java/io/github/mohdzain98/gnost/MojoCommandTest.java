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
    public void analyzeCiOptionsMirrorTheCommandLine() {
        AnalyzeMojo m = new AnalyzeMojo();
        m.failUnder = 7.5;
        m.baseline = "true"; // the flag alone: the default file
        m.writeBaseline = "ci/base.json";
        m.failOnNew = true;
        m.sarif = "true";
        m.badge = "docs/score.svg";
        assertEquals(
                Arrays.asList("g", "analyze", ".", "--fail-under", "7.5", "--baseline", "--write-baseline",
                        "ci/base.json", "--fail-on-new", "--sarif", "--badge", "docs/score.svg"),
                m.command("g"));
    }

    @Test
    public void emptyAndFalseValuesAddNothing() {
        AnalyzeMojo m = new AnalyzeMojo();
        m.baseline = "";
        m.sarif = "false";
        assertEquals(Arrays.asList("g", "analyze", "."), m.command("g"));
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
        assertTrue(m, m.contains("-Dgnost.downloadUrl=file:///"));
    }

    @Test
    public void spacesInArgumentsAreQuotedForDisplay() {
        assertEquals(Arrays.asList("g", "\"my dir\"", "x"), AbstractGnostMojo.quoted(Arrays.asList("g", "my dir", "x")));
    }

    @Test
    public void statsFoldersAndFilesShareTheScanOptions() {
        StatsMojo stats = new StatsMojo();
        stats.exclude = "target";
        assertEquals(Arrays.asList("g", "stats", ".", "--exclude", "target"), stats.command("g"));
        FoldersMojo folders = new FoldersMojo();
        folders.include = "src";
        assertEquals(Arrays.asList("g", "folders", ".", "--include", "src"), folders.command("g"));
        FilesMojo files = new FilesMojo();
        files.top = 10;
        files.progress = true;
        assertEquals(Arrays.asList("g", "files", ".", "--progress", "--top", "10"), files.command("g"));
    }

    @Test
    public void versionTakesNoFolder() {
        assertEquals(Arrays.asList("g", "version"), new VersionMojo().command("g"));
    }

    @Test
    public void openTakesATargetAndCanSkipTheBrowser() {
        OpenMojo m = new OpenMojo();
        m.target = "flow";
        m.open = false;
        assertEquals(Arrays.asList("g", "open", "flow", "--no-open"), m.command("g"));
        OpenMojo d = new OpenMojo();
        d.open = true;
        assertEquals(Arrays.asList("g", "open", "report"), d.command("g"));
    }

    @Test
    public void initMirrorsTheIntegrationFlags() {
        InitMojo m = new InitMojo();
        m.pom = true;
        m.githubAction = true;
        m.forkComments = true;
        m.dryRun = true;
        m.agents = true;
        assertEquals(
                Arrays.asList("g", "init", ".", "--dry-run", "--pom", "--github-action", "--fork-comments",
                        "--agents"),
                m.command("g"));
    }

    @Test
    public void changesPutsTheRefsBeforeTheFolder() {
        ChangesMojo m = new ChangesMojo();
        m.refs = "origin/main";
        m.depth = 2;
        m.format = "markdown";
        m.findings = true;
        m.noWrite = true;
        assertEquals(
                Arrays.asList("g", "changes", "origin/main", ".", "--depth", "2", "--format", "markdown",
                        "--findings", "--no-write"),
                m.command("g"));
    }

    @Test
    public void repositoryGoalsPassTheBranchOfARemoteAddress() {
        OnboardMojo m = new OnboardMojo();
        m.path = "https://github.com/owner/repo";
        m.ref = "v1.0";
        assertEquals(Arrays.asList("g", "onboard", "https://github.com/owner/repo", "--ref", "v1.0"), m.command("g"));
        assertTrue(m.pathIsAddress());
        m.path = "src";
        assertTrue(!m.pathIsAddress());
        m.path = "git@github.com:owner/repo.git";
        assertTrue(m.pathIsAddress());
    }

    @Test
    public void onboardCanSwitchTheProgressBarOff() {
        OnboardMojo m = new OnboardMojo();
        m.noProgress = true;
        assertEquals(Arrays.asList("g", "onboard", ".", "--no-progress"), m.command("g"));
    }

    @Test
    public void onboardCanPutTheProjectMapInTheReadme() {
        OnboardMojo m = new OnboardMojo();
        m.threeD = true;
        m.injectMindmap = true;
        m.mindmapFormat = "mermaid";
        assertEquals(Arrays.asList("g", "onboard", ".", "--3d", "--inject-mindmap", "--mindmap-format", "mermaid"),
                m.command("g"));
    }

    @Test
    public void summaryCanCountLikeGitHub() {
        SummaryMojo m = new SummaryMojo();
        m.git = true;
        assertEquals(Arrays.asList("g", "summary", ".", "--git"), m.command("g"));
    }

    @Test
    public void analyzeRepeatsTheLanguageOption() {
        AnalyzeMojo m = new AnalyzeMojo();
        m.language = "typescript, javascript";
        assertEquals(
                Arrays.asList("g", "analyze", ".", "--language", "typescript", "--language", "javascript"),
                m.command("g"));
    }

    @Test
    public void changesCanFailOnArchitectureViolations() {
        ChangesMojo m = new ChangesMojo();
        m.refs = "origin/main";
        m.failOnViolations = true;
        assertEquals(
                Arrays.asList("g", "changes", "origin/main", ".", "--fail-on-violations"), m.command("g"));
    }
}
