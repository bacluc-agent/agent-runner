import sys, re
command_file = sys.argv[1]
content = open("AGENTS.md").read()
marker = "/completion-check-command"
idx = content.find(marker)
if idx == -1:
    sys.exit(0)
rest = content[idx:]
match = re.search(r"```bash\n(.*?)```", rest, re.DOTALL)
if match:
    open(command_file, "w").write(match.group(1).strip() + "\n")
