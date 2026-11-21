package io.github.mohdzain98.gnost;

import java.io.File;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Proxy;
import java.util.ArrayList;
import java.util.List;
import org.apache.maven.execution.MavenSession;
import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugin.MojoFailureException;
import org.apache.maven.plugins.annotations.Parameter;

/** Finds a GNOST executable (PATH, then the download cache) and runs one sub-command with it. */
public abstract class AbstractGnostMojo extends AbstractMojo {

    static final String DEFAULT_DOWNLOAD_URL = "https://github.com/mohdzain98/gnost/releases/download/v";

    @Parameter(defaultValue = "${session}", readonly = true, required = true)
    MavenSession session;

    /** Folder to scan. Defaults to the directory Maven was started in. */
    @Parameter(property = "gnost.path")
    String path;

    /** Use this gnost executable and skip the PATH lookup and the download. */
    @Parameter(property = "gnost.binary")
    File binary;

    /** Skip the run. */
    @Parameter(property = "gnost.skip", defaultValue = "false")
    boolean skip;

    /** Extra command-line arguments, split on spaces, added at the end. */
    @Parameter(property = "gnost.args")
    String args;

    /** Where downloaded binaries are kept. Defaults to ~/.gnost. */
    @Parameter(property = "gnost.home")
    File home;

    /**
     * Folder (or mirror) that holds the release files gnost-VERSION-PLATFORM.tar.gz or .zip.
     * Defaults to the GitHub Release of the same version.
     */
    @Parameter(property = "gnost.downloadUrl")
    String downloadUrl;

    /** The gnost sub-command, such as onboard. */
    abstract String subcommand();

    /** Add this goal's options (after its arguments) to the command. */
    abstract void addOptions(List<String> cmd);

    /** Add the positional arguments; most goals take the folder to scan. */
    void addArguments(List<String> cmd) {
        cmd.add(path != null && !path.isEmpty() ? path : ".");
    }

    /** True when the path is a repository address; results then go to the working directory. */
    boolean pathIsAddress() {
        return path != null && path.matches("(?i)^(https?|ssh|git)://.*|^[\\w.-]+@[\\w.-]+:.*");
    }

    @Override
    public void execute() throws MojoExecutionException, MojoFailureException {
        if (skip) {
            getLog().info("GNOST skipped (gnost.skip)");
            return;
        }
        File dir = workingDirectory();
        File exe = locate();
        List<String> cmd = command(exe.getAbsolutePath());
        File target = new File(path != null && !path.isEmpty() && !pathIsAddress() ? path : ".");
        if (!target.isAbsolute()) {
            target = new File(dir, target.getPath());
        }
        OutputWatcher watcher = new OutputWatcher(target);
        watcher.snapshot();
        getLog().info("gnost command: " + String.join(" ", quoted(cmd)));
        getLog().info("gnost working directory: " + dir.getAbsolutePath());
        int code;
        try {
            code = new ProcessBuilder(cmd).directory(dir).inheritIO().start().waitFor();
        } catch (IOException e) {
            throw new MojoExecutionException("could not start " + exe + ": " + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new MojoExecutionException("interrupted while running gnost", e);
        }
        reportOutputs(watcher);
        if (code != 0) {
            throw new MojoFailureException("gnost " + subcommand() + " exited with code " + code);
        }
    }

    /** The full command line for the given executable. */
    List<String> command(String exe) {
        List<String> cmd = new ArrayList<String>();
        cmd.add(exe);
        cmd.add(subcommand());
        addArguments(cmd);
        addOptions(cmd);
        if (args != null && !args.trim().isEmpty()) {
            for (String a : args.trim().split("\\s+")) {
                cmd.add(a);
            }
        }
        return cmd;
    }

    private File workingDirectory() {
        String root = session != null ? session.getExecutionRootDirectory() : null;
        return new File(root != null ? root : System.getProperty("user.dir"));
    }

    private void reportOutputs(OutputWatcher watcher) {
        List<String> written = watcher.changes();
        if (written.isEmpty()) {
            getLog().info("gnost wrote no files (this command only prints, or nothing changed)");
            return;
        }
        getLog().info("gnost wrote:");
        for (String w : written) {
            getLog().info("  " + w);
        }
    }

    /** Pick the executable: -Dgnost.binary, then a matching gnost on PATH, then the cache or download. */
    private File locate() throws MojoExecutionException {
        PluginInfo info;
        try {
            info = PluginInfo.load();
        } catch (IOException e) {
            throw new MojoExecutionException(e.getMessage(), e);
        }
        if (binary != null) {
            if (!binary.isFile()) {
                throw new MojoExecutionException("-Dgnost.binary does not point to a file: " + binary);
            }
            getLog().info("gnost executable: " + binary.getAbsolutePath() + " (from -Dgnost.binary)");
            getLog().info("gnost cache: not used");
            return binary;
        }
        String os = System.getProperty("os.name");
        File onPath = PathFinder.find(System.getenv("PATH"), Platform.isWindows(os));
        if (onPath != null && acceptable(onPath, info)) {
            getLog().info("gnost executable: " + onPath.getAbsolutePath() + " (found on PATH)");
            getLog().info("gnost cache: not used");
            return onPath;
        }
        return download(info, os);
    }

    private boolean acceptable(File onPath, PluginInfo info) {
        String want = info.releaseVersion();
        String have = PathFinder.versionOf(onPath);
        if (want == null) {
            getLog().info("Using gnost from PATH (this plugin build has no release version to compare with)");
            return true;
        }
        if (want.equals(have)) {
            return true;
        }
        getLog().warn("gnost " + (have == null ? "(version unknown)" : have) + " on PATH at " + onPath
                + " does not match this plugin's version " + want + "; ignoring it and using version "
                + want + " from the download cache. Upgrade it (pip install -U gnost) to use it instead.");
        return false;
    }

    private File download(PluginInfo info, String os) throws MojoExecutionException {
        String key = Platform.current();
        if (key == null) {
            throw new MojoExecutionException("GNOST has no prebuilt binary for " + os + "/"
                    + System.getProperty("os.arch") + ". " + installHint());
        }
        String release = info.releaseVersion();
        if (release == null) {
            throw new MojoExecutionException("this plugin was built without a GNOST release to download "
                    + "(a local build). Put gnost on PATH or use -Dgnost.binary=/path/to/gnost.");
        }
        File cacheHome = home != null ? home : new File(System.getProperty("user.home"), ".gnost");
        String base = downloadUrl != null && !downloadUrl.trim().isEmpty()
                ? downloadUrl.trim() : DEFAULT_DOWNLOAD_URL + release;
        Provisioner p = new Provisioner(cacheHome, release, key, base, info.sha256(key),
                Platform.isWindows(os), mavenProxy(), new Provisioner.Log() {
                    @Override
                    public void info(String message) {
                        getLog().info(message);
                    }
                });
        getLog().info("gnost cache: " + p.cacheDir().getAbsolutePath());
        try {
            File exe = p.ensure();
            getLog().info("gnost executable: " + exe.getAbsolutePath() + " (from the cache)");
            return exe;
        } catch (IOException e) {
            throw new MojoExecutionException(failureMessage(e.getMessage(), p.url()), e);
        }
    }

    static String failureMessage(String reason, String url) {
        return "gnost was not found on PATH and could not be downloaded (" + reason + ").\n"
                + "If this network only reaches Maven Central, install gnost where Maven can find it, then run Maven again:\n"
                + "  " + installHint() + "\n"
                + "Or download the file yourself (for example with curl) and run Maven with\n"
                + "  -Dgnost.downloadUrl=file:///folder/that/holds/it\n"
                + "Download address tried: " + url;
    }

    static String installHint() {
        return "pipx install gnost   (or: npm install --global gnost-cli), "
                + "or point -Dgnost.binary at an installed gnost, or set -Dgnost.downloadUrl to a mirror.";
    }

    /** The active proxy from Maven's settings.xml, or null to let the JVM's own settings apply. */
    private Proxy mavenProxy() {
        if (session == null || session.getSettings() == null) {
            return null;
        }
        org.apache.maven.settings.Proxy p = session.getSettings().getActiveProxy();
        if (p == null || p.getHost() == null || p.getHost().isEmpty()) {
            return null;
        }
        return new Proxy(Proxy.Type.HTTP, new InetSocketAddress(p.getHost(), p.getPort()));
    }

    static List<String> quoted(List<String> cmd) {
        List<String> out = new ArrayList<String>();
        for (String c : cmd) {
            out.add(c.matches(".*\\s.*") ? "\"" + c + "\"" : c);
        }
        return out;
    }

    static void flag(List<String> cmd, boolean on, String name) {
        if (on) {
            cmd.add(name);
        }
    }

    /** An option whose value is a file: "true" means the flag alone (its default file). */
    static void optionalValue(List<String> cmd, String value, String name) {
        if (value == null || value.trim().isEmpty() || value.trim().equalsIgnoreCase("false")) {
            return;
        }
        cmd.add(name);
        if (!value.trim().equalsIgnoreCase("true")) {
            cmd.add(value.trim());
        }
    }

    static void option(List<String> cmd, Object value, String name) {
        if (value != null) {
            cmd.add(name);
            cmd.add(String.valueOf(value));
        }
    }
}
