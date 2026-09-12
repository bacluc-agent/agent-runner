import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("_chatgpt_login_impl", Path(__file__).with_name("chatgpt-login.py"))
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
build_auth_json = _mod.build_auth_json
write_auth_file = _mod.write_auth_file
main = _mod.main
