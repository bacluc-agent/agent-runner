---
name: git-history
description: Keep agent-created commits clean before every push.
---

Before pushing a branch, run `python3 scripts/check_git_history.py --base <base> --head <branch> --repo <repo>`. Fix every reported violation in the commit that introduced it; amend rather than append a correction. Re-run the gate until it exits zero. Keep commits linear, conventional, at most 72 characters, and limited to one concern. Land a green refactor commit before behavior changes. Never use merge commits or a catch-all staging commit.
