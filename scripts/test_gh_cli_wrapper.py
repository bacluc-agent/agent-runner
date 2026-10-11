import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FAKE = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
if sys.argv[1:] == ["alias", "list"]:
    print(os.environ.get("TEST_ALIASES", ""), end="")
    sys.exit(int(os.environ.get("TEST_ALIAS_STATUS", "0")))
with Path(os.environ["TEST_LOG"]).open("a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
print(json.dumps({"argv": sys.argv[1:], "stdin": sys.stdin.read()}))
print("backend stderr", file=sys.stderr)
sys.exit(int(os.environ.get("TEST_STATUS", "0")))
'''


def prepare_backend(directory):
    backend = directory / "bin" / "gh"
    backend.parent.mkdir(parents=True, exist_ok=True)
    backend.write_text(FAKE)
    backend.chmod(0o755)
    return backend


def verify_installed():
    with tempfile.TemporaryDirectory() as directory:
        env = dict(os.environ, TEST_LOG=str(Path(directory) / "log"), TEST_STATUS="23")
        argv = ["pr", "create", "-R", "BaClUc-AgEnT/ecamp3", "--title", "T", "--head", "br",
                "--base", "main", "--body-file", "-"]
        expected = ["api", "repos/BaClUc-AgEnT/ecamp3/pulls", "-X", "POST", "--jq", ".html_url",
                    "-f", "title=T", "-f", "head=br", "-f", "base=main", "-f", "body=body from stdin"]
        result = subprocess.run(["bash", "-c", 'exec gh "$@"', "test", *argv],
                                cwd=directory, env=env, input="body from stdin",
                                capture_output=True, text=True)
        assert result.returncode == 23, result.stderr
        assert json.loads(result.stdout) == {"argv": expected, "stdin": ""}
        assert result.stderr == "backend stderr\n"
        log = Path(env["TEST_LOG"])
        log.unlink()
        result = subprocess.run(["bash", "-c", 'gh pr create -R ecamp/ecamp3 --base devel --head bacluc-agent:issue-221-move-doctrine-validate-to-required-ci'],
                                cwd=directory, env=env, capture_output=True, text=True)
        assert result.returncode != 0
        assert "gh cli wrapper:" in result.stderr
        assert not log.exists()
        for denied in ("gh pr create -R ecamp/ecamp3 --repo ecamp/ecamp3",
                       "gh pr create --repo ecamp/ecamp3 --base devel --head bacluc-agent:issue-221-move-doctrine-validate-to-required-ci"):
            result = subprocess.run(["bash", "-c", denied], cwd=directory, env=env,
                                    capture_output=True, text=True)
            assert result.returncode != 0, denied
            assert "gh cli wrapper:" in result.stderr, denied
            assert not log.exists(), denied
    print("Installed composite wrapper: forwarding and historical denial passed")


class CliWrapperTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.backend = prepare_backend(self.directory)
        self.env = dict(os.environ, RUNNER_TEMP=str(self.directory),
                        GITHUB_PATH=str(self.directory / "path"),
                        PATH=f"{self.backend.parent}:{os.environ['PATH']}",
                        TEST_LOG=str(self.directory / "log"), GH_HOST="github.com")
        result = subprocess.run(["bash", str(ROOT / "scripts/install-gh-cli-wrapper.sh")],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.env["PATH"] = f"{(self.directory / 'path').read_text().strip()}:{self.env['PATH']}"

    def call(self, argv, allowed=True, expect=None, **env):
        log = Path(self.env["TEST_LOG"])
        log.unlink(missing_ok=True)
        result = subprocess.run(["bash", "-c", 'exec gh "$@"', "test", *argv],
                                cwd="/tmp", env=dict(self.env, **env), input="payload\n",
                                capture_output=True, text=True)
        if allowed:
            self.assertEqual(result.returncode, int(env.get("TEST_STATUS", "0")), result.stderr)
            if expect is None:
                self.assertEqual(json.loads(result.stdout), {"argv": argv, "stdin": "payload\n"})
                self.assertEqual(result.stderr, "backend stderr\n")
                self.assertEqual(log.read_text().splitlines(), [json.dumps(argv)])
            else:
                self.assertEqual(json.loads(result.stdout)["argv"], expect)
                self.assertIn(json.dumps(expect), log.read_text())
        else:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("gh cli wrapper:", result.stderr)
            self.assertFalse(log.exists(), result.stdout)

    def test_creation(self):
        self.call(["pr", "create", "-R", "ecamp/ecamp3", "--base", "devel", "--head",
                   "bacluc-agent:issue-221-move-doctrine-validate-to-required-ci"], False)
        for command in ("create", "new"):
            for repo in ("BacLuc/r", "BaClUc-AgEnT/r", "bacluc-agent-org/r",
                         "github.com/BacLuc/r", "https://github.com/BacLuc/r"):
                canonical = repo.removeprefix("https://github.com/").removeprefix("github.com/")
                rest = ["api", f"repos/{canonical}/pulls", "-X", "POST", "--jq", ".html_url",
                        "-f", "title=T", "-f", "head=br", "-f", "base=main"]
                for flags in (["-R", repo], ["-R" + repo], ["-R=" + repo], ["--repo", repo], ["--repo=" + repo]):
                    self.call(["pr", command, *flags, "--title", "T", "--head", "br", "--base", "main"],
                              expect=rest)
            for flags in ([], ["-R", "outsider/r"], ["-R", "BacLuc-evil/r"],
                          ["-R", "evil.com/BacLuc/r"], ["-R", "BacLuc/r", "--repo", "BacLuc/r"],
                          ["-R", "ecamp/ecamp3", "--repo", "ecamp/ecamp3"], ["--repo", "ecamp/ecamp3"],
                          ["--body", "--repo=BacLuc/r"], ["--title=-RBacLuc/r"],
                          ["-R", "BacLuc/r", "--unknown"], ["-R"], ["--", "-R", "BacLuc/r"]):
                self.call(["pr", command, *flags], False)
        self.call(["pr", "-RBacLuc/r", "create", "--title", "T", "--head", "br", "--base", "main"],
                  expect=["api", "repos/BacLuc/r/pulls", "-X", "POST", "--jq", ".html_url",
                          "-f", "title=T", "-f", "head=br", "-f", "base=main"])
        self.call(["pr", "create", "-RBacLuc/r"], False, GH_HOST="evil.com")

    def test_pr_create_translation(self):
        base = ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main"]
        rest = ["api", "repos/BacLuc/r/pulls", "-X", "POST", "--jq", ".html_url",
                "-f", "title=T", "-f", "head=br", "-f", "base=main"]
        self.call(base, expect=rest)
        self.call(base + ["--draft"], expect=rest + ["-F", "draft=true"])
        self.call(base + ["--body", "hello"], expect=rest + ["-f", "body=hello"])
        with tempfile.NamedTemporaryFile("w", delete=False) as body_file:
            body_file.write("body from file")
            body_path = body_file.name
        self.addCleanup(lambda: os.unlink(body_path))
        self.call(base + ["--body-file", body_path], expect=rest + ["-f", "body=body from file"])
        self.call(base + ["--body-file", "-"], expect=rest + ["-f", "body=payload\n"])
        self.call(["pr", "new", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main"],
                  expect=rest)
        for repo in ("-RBacLuc/r", "-R=BacLuc/r", "--repo=BacLuc/r"):
            self.call(["pr", "create", repo, "--title", "T", "--head", "br", "--base", "main"],
                      expect=rest)
        for repo in ("github.com/BacLuc/r", "https://github.com/BacLuc/r"):
            self.call(["pr", "create", "-R", repo, "--title", "T", "--head", "br", "--base", "main"],
                      expect=rest)
        self.call(["pr", "create", "--help"])
        for denied in (
            ["pr", "create", "-R", "BacLuc/r", "--head", "br", "--base", "main"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--base", "main"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--body", "x", "--body-file", "y"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--body-file", "missing-file"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--reviewer", "alice"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "-r", "alice"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--label", "bug"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "-l", "bug"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--milestone", "1"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "-m", "1"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--assignee", "alice"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "-a", "alice"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--project", "x"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "-p", "x"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "-T", "tpl"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--fill"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--fill-first"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--fill-verbose"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--web"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--dry-run"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--recover", "x"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--attach", "f"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "--no-maintainer-edit"],
            ["pr", "create", "-R", "BacLuc/r", "--title", "T", "--head", "br", "--base", "main",
             "-e"],
        ):
            self.call(denied, False)

    def test_api(self):
        for endpoint in ("repos/ecamp/ecamp3/pulls", "/repos/ecamp/ecamp3/pulls", "https://api.github.com/repos/ecamp/ecamp3/pulls"):
            for flags in (["-X", "POST"], ["--method=POST"], ["-XPOST"], ["-f", "title=test"], ["-Ftitle=test"], ["--input", "-"]):
                self.call(["api", endpoint, *flags], False)
                self.call(["api", endpoint.replace("ecamp/ecamp3", "BaClUc-AgEnT/r"), *flags])
            self.call(["api", endpoint])
            self.call(["api", endpoint, "-XGET", "-f", "q=hello"])
        for endpoint in ("graphql", "/graphql", "https://api.github.com/graphql", "repos/{owner}/{repo}/pulls",
                         "repos/ecamp/ecamp3/pulls/", "repos/BacLuc/r/../r/pulls", "repos/BacLuc/r/%70ulls",
                         "repos/BacLuc/r//pulls", "repos/BacLuc/r/pulls?x=1", "https://evil.com/repos/BacLuc/r/pulls",
                         "https://api.github.com//repos/BacLuc/r/pulls", "repositories/123/pulls",
                         "api/v3/repos/BacLuc/r/pulls"):
            self.call(["api", endpoint, "--input=-"], False)
        for flags in (["--hostname", "evil.com"], ["--hostname=github.com", "--hostname=github.com"],
                      ["-XPOST", "-XGET"], ["-HHost:evil.com"], ["-HX-HTTP-Method-Override:POST"],
                      ["--unknown"], ["repos/BacLuc/r/pulls"]):
            self.call(["api", "repos/ecamp/ecamp3/pulls", *flags], False)
        self.call(["api", "repos/BacLuc/r/pulls/", "-X", "POST", "-f", "title=test"])
        self.call(["api", "repos/BacLuc/r/contents/", "--jq", ".[].name"])
        self.call(["api", "graphql", "-XGET"], False)
        self.call(["api", "repos/BacLuc/r/pulls", "-f", "body=--hostname=evil.com", "--hostname=github.com"])

    def test_revert(self):
        for argv in (
            ["pr", "revert", "123", "-R", "ecamp/ecamp3", "--title", "Revert change", "--body", "Revert change"],
            ["pr", "-R", "ecamp/ecamp3", "revert", "123"],
            ["pr", "--repo=ecamp/ecamp3", "revert", "123"],
            ["pr", "revert", "https://github.com/ecamp/ecamp3/pull/123"],
            ["pr", "revert", "123"],
            ["pr", "revert", "123", "-R", "BacLuc/r", "-R", "ecamp/ecamp3"],
            ["pr", "revert", "-R", "BacLuc/r"],
            ["pr", "revert", "--help"],
            ["pr", "revert", "123", "-R", "BacLuc/r", "--unknown"],
            ["api", "repos/ecamp/ecamp3/pulls/123/reverts", "-XPOST"],
            ["api", "repos/ecamp/ecamp3/pulls/123/reverts", "-f", "title=test"],
        ):
            self.call(argv, False)
        for argv in (
            ["pr", "revert", "123", "-R", "BaClUc-AgEnT/r", "--title", "Revert change", "--body", "Revert change"],
            ["pr", "revert", "https://github.com/BacLuc/r/pull/123"],
            ["pr", "-R", "BacLuc/r", "revert", "123"],
            ["api", "repos/BacLuc/r/pulls/123/reverts", "-XPOST"],
            ["api", "repos/ecamp/ecamp3/pulls/123/reverts", "-XGET"],
        ):
            self.call(argv)

    def test_other_calls_and_aliases(self):
        for argv in (["pr", "view", "10800", "-R", "ecamp/ecamp3"], ["search", "issues", "test"],
                     ["repo", "fork", "ecamp/ecamp3", "--org", "bacluc-agent"],
                     ["repo", "fork", "BacLuc/r", "--org", "bacluc-agent-org"],
                     ["issue", "comment", "234", "-R", "BaClUc-AgEnT/r", "--body", "hello"],
                     ["issue", "create", "-R", "BacLuc/r", "-t", "x", "-b", "y"],
                     ["issue", "edit", "234", "-R", "bacluc-agent-org/r", "-b", "y"],
                     ["issue", "close", "https://github.com/BacLuc/r/issues/1"],
                     ["workflow", "run", "ci.yml", "-R", "bacluc-agent/r", "--ref", "main"],
                     ["run", "cancel", "123", "-R", "BacLuc/r"],
                     ["run", "rerun", "123", "-R", "bacluc-agent/r"],
                     ["run", "delete", "123", "-R", "BacLuc/r"],
                     ["cache", "delete", "key", "-R", "BacLuc/r"],
                     ["release", "download", "v1", "-R", "BacLuc/r"],
                     ["api", "search/issues", "-XGET", "-fq=repo:ecamp/ecamp3"],
                     ["api", "repos/bacluc-agent-org/r/issues", "-fbody=x"]):
            self.call(argv, TEST_STATUS="17")
        for argv in (["issue", "comment", "234", "-R", "outsider/r", "--body", "pr create"],
                     ["issue", "create", "-t", "x", "-b", "y"],
                     ["issue", "comment", "234", "--body", "x"],
                     ["issue", "edit", "234", "-R", "outsider/r", "-b", "x"],
                     ["repo", "fork", "ecamp/ecamp3"],
                     ["repo", "fork", "ecamp/ecamp3", "--org", "outsider"],
                     ["repo", "delete", "outsider/r"],
                     ["repo", "edit", "ecamp/ecamp3", "-d", "x"],
                     ["workflow", "run", "ci.yml", "--ref", "issue-234"],
                     ["workflow", "run", "ci.yml", "-R", "outsider/r"],
                     ["workflow", "disable", "ci.yml", "-R", "outsider/r"],
                     ["run", "cancel", "123", "-R", "outsider/r"],
                     ["cache", "delete", "key", "-R", "outsider/r"],
                     ["api", "repos/ecamp/ecamp3/issues/1/comments", "-fbody=test"],
                     ["api", "repos/{owner}/{repo}/issues/comments/1", "-XPATCH", "-fbody=test"],
                     ["api", "repos/ecamp/ecamp3/forks", "-XPOST"],
                     ["api", "repos/ecamp/ecamp3/actions/workflows/ci.yml/dispatches", "-fref=main"]):
            self.call(argv, False)
        for argv in (["alias", "set", "p", "pr create"], ["extension", "exec", "p"], ["extensions", "exec", "p"],
                     ["custom"], ["--repo=BacLuc/r", "pr", "create"]):
            self.call(argv, False)
        self.call(["pr", "view"], False, TEST_ALIASES="pr: !echo bypass\n")
        self.call(["pr", "view"], False, TEST_ALIAS_STATUS="1")
        self.call(["pr", "view"], TEST_ALIASES="co: pr checkout\n")

    def test_subsequent_step_probe(self):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--verify-installed"],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_installer_recursion_and_missing_backend(self):
        result = subprocess.run(["bash", str(ROOT / "scripts/install-gh-cli-wrapper.sh")],
                                env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gh cli wrapper:", result.stderr)
        self.backend.unlink()
        self.call(["pr", "view"], False)
        empty = self.directory / "empty"
        empty.mkdir()
        result = subprocess.run(["/bin/bash", str(ROOT / "scripts/install-gh-cli-wrapper.sh")],
                                env=dict(self.env, PATH=str(empty)), capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gh cli wrapper:", result.stderr)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--prepare-backend":
        print(prepare_backend(Path(sys.argv[2])).parent)
    elif sys.argv[1:] == ["--verify-installed"]:
        verify_installed()
    else:
        unittest.main()
