package io.github.mohdzain98.gnost;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;
import org.apache.maven.execution.MavenSession;
import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugin.MojoFailureException;
import org.apache.maven.plugins.annotations.Component;
import org.apache.maven.plugins.annotations.Parameter;
import org.eclipse.aether.RepositorySystem;
import org.eclipse.aether.RepositorySystemSession;
import org.eclipse.aether.artifact.DefaultArtifact;
import org.eclipse.aether.repository.RemoteRepository;
import org.eclipse.aether.resolution.ArtifactRequest;
import org.eclipse.aether.resolution.ArtifactResolutionException;

/** Finds the GNOST binary for this machine and runs one sub-command with it. */
public abstract class AbstractGnostMojo extends AbstractMojo {

    static final String GROUP_ID = "io.github.mohdzain98";
    static final String BINARY_ARTIFACT = "gnost-binary";

    @Parameter(defaultValue = "${session}", readonly = true, required = true)
    MavenSession session;

    @Parameter(defaultValue = "${repositorySystemSession}", readonly = true)
    RepositorySystemSession repoSession;

    @Parameter(defaultValue = "${project.remotePluginRepositories}", readonly = true)
    List<RemoteRepository> remoteRepos;

    @Component
    RepositorySystem repoSystem;

    /** Folder to scan. Defaults to the directory Maven was started in. */
    @Parameter(property = "gnost.path")
    String path;

    /** Use this gnost executable instead of the one from Maven. */
    @Parameter(property = "gnost.binary")
    File binary;

    /** Skip the run. */
    @Parameter(property = "gnost.skip", defaultValue = "false")
    boolean skip;

    /** Extra command-line arguments, split on spaces, added at the end. */
    @Parameter(property = "gnost.args")
    String args;

    /** The gnost sub-command, such as onboard. */
    abstract String subcommand();

    /** Add this goal's options (after the path) to the command. */
    abstract void addOptions(List<String> cmd);

    @Override
    public void execute() throws MojoExecutionException, MojoFailureException {
        if (skip) {
            getLog().info("GNOST skipped (gnost.skip)");
            return;
        }
        File exe = binary != null ? binary : resolveBinary();
        File dir = workingDirectory();
        List<String> cmd = command(exe.getAbsolutePath());
        getLog().info("Running: gnost " + String.join(" ", cmd.subList(1, cmd.size())));
        int code;
        try {
            code = new ProcessBuilder(cmd).directory(dir).inheritIO().start().waitFor();
        } catch (IOException e) {
            throw new MojoExecutionException("could not start " + exe + ": " + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new MojoExecutionException("interrupted while running gnost", e);
        }
        if (code != 0) {
            throw new MojoFailureException("gnost " + subcommand() + " exited with code " + code);
        }
    }

    /** The full command line for the given executable. */
    List<String> command(String exe) {
        List<String> cmd = new ArrayList<String>();
        cmd.add(exe);
        cmd.add(subcommand());
        cmd.add(path != null && !path.isEmpty() ? path : ".");
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

    private File resolveBinary() throws MojoExecutionException {
        String classifier = Platform.current();
        String os = System.getProperty("os.name") + "/" + System.getProperty("os.arch");
        if (classifier == null) {
            throw new MojoExecutionException(unsupported(os));
        }
        String version = pluginVersion();
        try {
            DefaultArtifact artifact =
                    new DefaultArtifact(GROUP_ID, BINARY_ARTIFACT, classifier, "zip", version);
            File zip = repoSystem
                    .resolveArtifact(repoSession, new ArtifactRequest(artifact, remoteRepos, null))
                    .getArtifact()
                    .getFile();
            return BinaryUnpacker.prepare(zip, Platform.isWindows(System.getProperty("os.name")));
        } catch (ArtifactResolutionException e) {
            throw new MojoExecutionException(unsupported(os) + " (could not fetch " + classifier + ": "
                    + e.getMessage() + ")", e);
        } catch (IOException e) {
            throw new MojoExecutionException("could not prepare the GNOST binary: " + e.getMessage(), e);
        }
    }

    private static String unsupported(String os) {
        return "GNOST has no standalone binary for " + os + " in this release. "
                + "Use Docker (ghcr.io/mohdzain98/gnost), or 'uvx gnost' / 'npx gnost-cli', "
                + "or point -Dgnost.binary at an installed gnost.";
    }

    static String pluginVersion() throws MojoExecutionException {
        try (InputStream in = AbstractGnostMojo.class.getResourceAsStream("/gnost-plugin.properties")) {
            Properties p = new Properties();
            p.load(in);
            return p.getProperty("version");
        } catch (IOException | RuntimeException e) {
            throw new MojoExecutionException("plugin version not found", e);
        }
    }

    static void flag(List<String> cmd, boolean on, String name) {
        if (on) {
            cmd.add(name);
        }
    }

    static void option(List<String> cmd, Object value, String name) {
        if (value != null) {
            cmd.add(name);
            cmd.add(String.valueOf(value));
        }
    }
}
