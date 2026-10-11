#!/usr/bin/env python3
import os
from pathlib import Path
import re
import subprocess
import sys


OWNED_ORGS = {"bacluc", "bacluc-agent", "bacluc-agent-org"}

MUTATIONS = {
    "issue": {"create", "edit", "close", "reopen", "comment", "delete", "transfer", "lock", "unlock",
              "pin", "unpin", "develop", "clone"},
    "repo": {"create", "edit", "delete", "archive", "rename", "fork", "sync", "transfer", "unarchive",
             "set-default", "gc", "credits"},
    "workflow": {"run", "enable", "disable", "delete", "cancel"},
    "run": {"cancel", "rerun", "delete"},
    "cache": {"delete"},
    "discussion": {"create", "edit", "delete", "close", "reopen", "comment", "transfer", "pin", "unpin"},
    "label": {"create", "edit", "delete", "clone"},
    "release": {"create", "edit", "delete", "upload", "delete-asset"},
    "secret": {"set", "delete"},
    "variable": {"set", "delete"},
    "ruleset": {"create", "edit", "delete", "check"},
    "project": {"create", "edit", "delete", "close", "copy", "item-add", "item-create", "item-edit",
                "item-archive", "item-delete", "field-create", "field-delete", "link", "unlink",
                "mark-template"},
}


def deny(reason):
    raise ValueError(reason)


def owned_org(org):
    if org.lower() not in OWNED_ORGS:
        deny("use a bacluc-owned organization, not the upstream repository")


def owned_repo(repo):
    repo = re.sub(r"^(https://)?github\.com/", "", repo, flags=re.IGNORECASE)
    if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", repo):
        deny("use an explicit github.com OWNER/REPO")
    owner, name = repo.split("/")
    if owner.lower() not in OWNED_ORGS or name in {".", ".."}:
        deny("create the PR in the bacluc-agent fork, not the upstream repository")
    return repo


def options(args, values, switches):
    if isinstance(switches, set):
        switches = {flag: flag for flag in switches}
    positional, parsed = [], {}
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if not arg.startswith("-"):
            positional.append(arg)
            continue
        key, separator, value = arg.partition("=")
        if arg.startswith("-") and not arg.startswith("--") and len(arg) > 2:
            key, separator, value = arg[:2], "=", arg[2:].removeprefix("=")
        if key in values:
            if not separator:
                if index == len(args):
                    deny(f"missing value for {key}")
                value = args[index]
                index += 1
            parsed.setdefault(values[key], []).append(value)
        elif key in switches and (not separator or value in {"true", "false"}):
            parsed.setdefault(switches[key], []).append(True)
        else:
            deny(f"unsupported or ambiguous option {key}")
    return positional, parsed


PR_CREATE_VALUES = {
    "-R": "repo", "--repo": "repo",
    "-t": "title", "--title": "title",
    "-b": "body", "--body": "body",
    "-F": "body_file", "--body-file": "body_file",
    "-B": "base", "--base": "base",
    "-H": "head", "--head": "head",
}
PR_CREATE_SWITCHES = {"-d": "draft", "--draft": "draft"}


def build_pr_create(prefix, args):
    positional, parsed = options(prefix + args, PR_CREATE_VALUES, PR_CREATE_SWITCHES)
    if positional:
        deny("PR creation does not accept positional arguments")
    repos = parsed.get("repo", [])
    if len(repos) != 1:
        deny("PR creation requires exactly one explicit -R/--repo destination")
    repo = owned_repo(repos[0])
    for required in ("title", "head", "base"):
        if required not in parsed:
            deny(f"gh pr create under the sandbox requires --{required}; GraphQL inference is unavailable, pass it explicitly")
    if "body" in parsed and "body_file" in parsed:
        deny("use either --body or --body-file, not both")
    fields = []
    for name in ("title", "head", "base"):
        fields += ["-f", f"{name}={parsed[name][-1]}"]
    if "body_file" in parsed:
        source = parsed["body_file"][-1]
        if source == "-":
            body = sys.stdin.read()
        else:
            try:
                body = Path(source).read_text()
            except OSError as error:
                deny(f"cannot read --body-file: {error}")
        fields += ["-f", f"body={body}"]
    elif "body" in parsed:
        fields += ["-f", f"body={parsed['body'][-1]}"]
    if "draft" in parsed:
        fields += ["-F", "draft=true"]
    return ["api", f"repos/{repo}/pulls", "-X", "POST", "--jq", ".html_url", *fields]


def validate_pr(args):
    prefix = []
    while args and (args[0] in {"-R", "--repo"} or args[0].startswith(("-R", "--repo="))):
        flag, *args = args
        prefix.append(flag)
        if flag in {"-R", "--repo"}:
            if not args:
                deny("missing repository")
            value, *args = args
            prefix.append(value)
    if not args or args[0].startswith("-"):
        deny("use gh pr SUBCOMMAND followed by options")
    if args[0] == "revert":
        validate_revert(prefix, args)
        return None
    if args[0] not in {"create", "new"}:
        return None
    if "--help" in prefix + args[1:]:
        return None
    return build_pr_create(prefix, args[1:])


def validate_revert(prefix, args):
    values = {key: "repo" for key in ("-R", "--repo")}
    values.update({key: key for key in ("-b", "--body", "-F", "--body-file", "-t", "--title")})
    positional, parsed = options(prefix + args[1:], values, {"-d", "--draft", "--help"})
    if len(positional) != 1:
        deny("PR revert requires exactly one PR number or github.com PR URL")
    repos = parsed.get("repo", [])
    if len(repos) > 1:
        deny("PR revert requires exactly one explicit -R/--repo destination")
    selector = positional[0]
    match = re.fullmatch(r"https?://github\.com/([^/]+/[^/]+)/pull/[0-9]+", selector, flags=re.IGNORECASE)
    url_repo = match.group(1) if match else None
    if repos:
        owned_repo(repos[0])
    if url_repo:
        owned_repo(url_repo)
    if not repos and not url_repo:
        deny("PR revert requires an explicit -R/--repo destination or a github.com PR URL")


def repo_of(selector):
    match = re.match(r"^https?://github\.com/([A-Za-z0-9-]+/[A-Za-z0-9_.-]+)", selector, flags=re.IGNORECASE)
    return match.group(1) if match else selector


def org_option(args):
    for index, arg in enumerate(args):
        if arg == "--org":
            return args[index + 1] if index + 1 < len(args) else None
        if arg.startswith("--org="):
            return arg.split("=", 1)[1]
    return None


def selectors_of(args):
    explicit, positional = [], []
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg in {"-R", "--repo"}:
            if index < len(args):
                explicit.append(args[index])
                index += 1
        elif arg.startswith("--repo="):
            explicit.append(arg.split("=", 1)[1])
        elif arg.startswith("-R") and len(arg) > 2:
            explicit.append(arg[2:].removeprefix("="))
        elif arg.startswith("-"):
            continue
        else:
            positional.append(arg)
    selectors = list(explicit)
    for value in positional:
        if re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", value) or re.match(
            r"^https?://github\.com/[^/]+/[^/?#]+", value, flags=re.IGNORECASE
        ):
            selectors.append(value)
    return selectors


def validate_mutation(command, args):
    if not args or args[0] not in MUTATIONS.get(command, ()):
        return
    subcommand = args[0]
    if command == "repo" and subcommand == "fork":
        org = org_option(args)
        if org is None:
            deny("repo fork requires an explicit --org in a bacluc-owned organization")
        owned_org(org)
        return
    if command == "repo" and subcommand == "create":
        org = org_option(args)
        if org is not None:
            owned_org(org)
        else:
            owned_repo(os.environ.get("GITHUB_REPOSITORY", ""))
        return
    selectors = selectors_of(args)
    if command in {"issue", "workflow"}:
        if len(selectors) != 1:
            deny(f"{command} mutations require exactly one explicit owned -R/--repo or URL selector")
        owned_repo(repo_of(selectors[0]))
        return
    if len(selectors) > 1:
        deny(f"{command} mutations allow at most one explicit owned repository selector")
    owned_repo(repo_of(selectors[0]) if selectors else os.environ.get("GITHUB_REPOSITORY", ""))


def validate_api(args):
    values = {key: key for key in ("--cache", "-q", "--jq", "-p", "--preview", "-t", "--template")}
    for name, flags in {
        "method": ("-X", "--method"), "host": ("--hostname",),
        "body": ("-f", "--raw-field", "-F", "--field", "--input"),
        "header": ("-H", "--header"),
    }.items():
        values.update(dict.fromkeys(flags, name))
    positional, parsed = options(args, values, {
        "-i", "--include", "--paginate", "--silent", "--slurp", "--verbose",
        "--help", "--allow-escape-sequences",
    })
    if len(positional) != 1 or len(parsed.get("method", [])) > 1 or len(parsed.get("host", [])) > 1:
        deny("API calls require one unambiguous endpoint, method and host")
    if parsed.get("host", ["github.com"])[0].lower() != "github.com":
        deny("only github.com is supported")
    for header in parsed.get("header", []):
        if header.partition(":")[0].lower() not in {
            "accept", "authorization", "content-type", "x-github-api-version", "user-agent",
        }:
            deny("unsupported API header; routing overrides are not allowed")
    method = parsed.get("method", ["POST" if parsed.get("body") else "GET"])[0]
    if method not in {"GET", "HEAD", "OPTIONS", "POST", "PATCH", "PUT", "DELETE"}:
        deny("unsupported HTTP method")
    endpoint = positional[0]
    if endpoint.startswith("https://api.github.com/"):
        endpoint = endpoint.removeprefix("https://api.github.com/")
    else:
        endpoint = endpoint.removeprefix("/")
    path, query, _ = endpoint.partition("?")
    path = path.rstrip("/")
    if path.lower() == "graphql":
        deny("direct GraphQL is disabled; use guarded gh pr create -R or REST instead")
    if not re.fullmatch(r"[A-Za-z0-9_{}.-]+(?:/[A-Za-z0-9_{}.-]+)*", path) or any(
        part in {".", ".."} for part in path.split("/")
    ):
        deny("use a canonical github.com REST path without encoding or routing overrides")
    if method not in {"GET", "HEAD", "OPTIONS"}:
        if query:
            deny("put mutation parameters in fields, not the endpoint URL")
        parts = path.split("/")
        if len(parts) < 3 or parts[0].lower() != "repos":
            deny("mutating API calls require a canonical repos/OWNER/REPO endpoint")
        owned_repo("/".join(parts[1:3]))
        if parts[-1].lower() == "pulls":
            if len(parts) != 4 or parts[0] != "repos" or parts[3] != "pulls":
                deny("PR creation requires the canonical repos/OWNER/REPO/pulls endpoint")
            owned_repo("/".join(parts[1:3]))
        elif parts[-1].lower() == "reverts":
            if len(parts) != 6 or parts[0] != "repos" or parts[3].lower() != "pulls":
                deny("PR revert requires the canonical repos/OWNER/REPO/pulls/N/reverts endpoint")
            owned_repo("/".join(parts[1:3]))


def main():
    backend = Path(__file__).resolve().with_name("real-gh").read_text().strip()
    if not os.path.isabs(backend) or not os.access(backend, os.X_OK) or Path(backend).resolve() == Path(__file__).resolve():
        deny("real gh backend is missing or recursive; reinstall the guard")
    args = sys.argv[1:]
    if not args or args[0] not in {
        "api", "auth", "browse", "cache", "codespace", "completion", "config", "discussion", "gist",
        "gpg-key", "help", "issue", "label", "org", "pr", "project", "release", "repo", "ruleset", "run",
        "search", "secret", "ssh-key", "status", "variable", "workflow", "version", "--version", "--help",
    }:
        deny("only builtin commands are supported; aliases and extensions are disabled")
    aliases = subprocess.run([backend, "alias", "list"], capture_output=True, text=True)
    if aliases.returncode:
        deny("cannot check configured gh aliases")
    if any(line.split(":", 1)[0].strip() == args[0] for line in aliases.stdout.splitlines()):
        deny("configured alias execution is disabled; use the builtin command explicitly")
    if os.environ.get("GH_HOST", "github.com").lower() != "github.com":
        deny("only github.com is supported")
    if args[0] == "pr":
        translated = validate_pr(args[1:])
        if translated is not None:
            os.execv(backend, [backend, *translated])
    elif args[0] == "api":
        validate_api(args[1:])
    else:
        validate_mutation(args[0], args[1:])
    os.execv(backend, [backend, *args])


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(f"gh cli wrapper: {error}", file=sys.stderr)
        sys.exit(1)
