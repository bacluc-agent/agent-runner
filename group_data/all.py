import os

ai_agent_devcontainer = {"enabled": True}

alacritty = {
    "enabled": True,
    "font_size": 12,
}

python = {
    "enabled": True,
    "uv": {
        "enabled": True,
    },
}

vshn_tools = {"enabled": True}

basicsetup = {
    "additional_tools": [
        "ansible-lint",
        "apt-transport-https",
        "bat",
        "build-essential",
        "clang",
        "cloc",
        # "chromium-browser",
        # "chromium-codecs-ffmpeg",
        # "chromium-browser-l18n",
        "cmake",
        "curl",
        "git",
        "graphviz",
        # "gpaste2",
        # "gnome-tweaks",
        # "nextcloud-desktop",
        "jq",
        "libglu1-mesa",
        "libgtk-3-dev",
        "libstdc++-12-dev",
        "net-tools",
        "ninja-build",
        "ocrmypdf",
        "pkg-config",
        "procps",
        "tig",
        "xz-utils",
        "yamllint",
    ],
    "basic_tools": [
        "dos2unix",
        "fd-find",
        # "firefox",
        "htop",
        "nano",
        "rsync",
        "tar",
        "tree",
        "unzip",
        "wget",
        "zip",
    ],
    "enabled": True,
    "locale": "en_US.UTF-8",
    "timezone": "Europe/Zurich",
}

docker = {
    "enabled": True,
    "daemon_config_folder": "/etc/docker",
    "provision_daemon_json": False,
}

backup_burp = {
    "enabled": False,
    "ppa": "ppa:vshn/backup",
    "ppa_list_filename": "vshn-ubuntu-backup-noble.sources",
    "secret_store_app_name": "burp",
    "secret_store_local_pw_instance": "personal-laptop-instance",
    "secret_store_server_instance": "personal-server-laptop-server",
}

bash = {
    "enabled": True,
}

shell_includes = {
    "enabled": False,
}

zsh = {
    "enabled": True,
    "enable_zsh_autosuggestions": False,
    "completions_dir": "/home/{user}/zsh/completions",
    "motd_path": "/etc/profile.d/update-motd.sh",
}

basic_utils = {
    "enabled": True,
    "enable_direnv": True,
    "enable_flutter": False,
    "enable_keepassxc": False,
    "enable_signal": False,
    "enable_java": True,
    "enable_ssh_config_dir": True,
    "ssh_config_paths_to_include": ["./config.d/*"],
    "enable_openvpn_config_import_network_manager": True,
    "enable_zoom": False,
    "enable_go": False,
    "ssh_key": {
        "enable": True,
        "filename": "id_ed25519",
    },
    "ssh_agent": {
        "enable": True,
    },
    "gcr_ssh_agent": {
        "enable": False,
    },
    "python": {
        "venvs": [],
    },
}

cleanup_scripts = {
    "enabled": True,
    "dir": "/usr/local/bin/cleanup_scripts.d",
}

update_packages_script = {
    "dir": "/usr/local/bin/update-script.d",
}

devcontainer_cli = {
    "enabled": True,
}

displaylink_driver = {
    "enabled": True,
}

charging_state_monitor = {
    "enabled": False,
}

firefox = {
    "enabled": True,
}

flatpak = {
    "enabled": True,
}

flatpaks: list[str] = []

fluxcd = {
    "enabled": False,
}

fzf = {
    "enabled": True,
}

git_lfs = {
    "enabled": True,
    # renovate: datasource=github-releases depName=git-lfs/git-lfs
    "git_lfs_version": "3.7.1",
    "git_lfs_checksum": "6b92b05c4588b4a5373b2b4102dbb302757d8ec6671da67cf9e4f9ccb01cd349",
}

gnome = {
    "enable_customize_gnome": False,
}

nvm = {
    "_sudo_for_global_install": False,
    # renovate: datasource=github-releases depName=nvm-sh/nvm
    "nvm_version": "v0.40.8",
    "enabled": True,
}

kubectl = {
    "enabled": True,
    # renovate: datasource=github-releases depName=itaysk/kubectl-neat
    "kubectl_neat_version": "2.0.4",
    # renovate: datasource=github-releases depName=robscott/kube-capacity
    "kubectl_capacity_version": "0.8.0",
    # renovate: datasource=github-releases depName=rajatjindal/kubectl-modify-secret
    "kubectl_modify_secret_version": "0.0.47",
    "enable_oidc_plugin": False,
}

tmux = {
    "enabled": True,
}

nvim = {
    "enabled": True,
}

lazygit = {
    "enabled": True,
    # renovate: datasource=github-releases depName=jesseduffield/lazygit
    "lazygit_version": "0.65.1",
    "lazygit_checksum": "971bc18be3ddd75f67462016eeda9bc5581644f90e5e961ec11b450ef60be894",
}

ollama = {
    "enabled": False,
    # renovate: datasource=github-releases depName=ollama/ollama
    "ollama_version": "0.32.5",
    "model": "qwen2.5:3b",
}

t3_code = {
    "enabled": False,
}

ask_ai = {
    "enabled": True,
    "endpoint": "https://router.requesty.ai/v1",
    "model": "novita/deepseek/deepseek-v3.2",
    # Set in local.py — written directly into ~/.config/aichat/config.yaml (mode 600)
    "api_key": "",
}

homebrew = {
    "enabled": True,
}

snap = {
    "enabled": True,
    "refresh": {
        "timer": "4:00-9:00",
    },
}

snaps: list[str] = []

classic_snaps: list[str] = []

sysctl = {
    "enabled": True,
    "settings": {
        "fs.inotify.max_queued_events": 1048576,
        "fs.inotify.max_user_instances": 1048576,
        "fs.inotify.max_user_watches": 1048576,
    },
}

motd = {
    "enable_disk_usage": False,
}

zed = {
    "enabled": True,
    "enable_helm_support": True,
    "enable_memory_monitor": True,
    "memory_monitor_limit_gb": 10,
    "memory_monitor_cron_frequency": "*/5 * * * *",
}

vifm = {
    "enabled": True,
}

jetbrains = {
    "enabled": False,
}

okular = {
    "enabled": True,
}

ubuntu_desktop = {
    "enabled": True,
    "enable_dependencies": True,
    "enable_favorite_apps": True,
    "enable_keyboard_layouts": True,
    "enable_shortcuts": True,
    "enable_gpaste_config": False,
    "enable_testing_browser_desktop": False,
    "favorite_apps": [
        {"desktop_file_name": "Alacritty.desktop", "shortcut": "<Super>y"},
        {"desktop_file_name": "firefox_firefox.desktop", "shortcut": "<Super>x"},
        {"desktop_file_name": "phpstorm_phpstorm.desktop", "shortcut": "<Super>r"},
        {"desktop_file_name": "dev.zed.Zed.desktop", "shortcut": "<Super>f"},
        {"desktop_file_name": "org.mozilla.Thunderbird.desktop", "shortcut": "<Super><Alt>c"},
    ],
}

hashicorp_apt_repo = {
    "enabled": False,
}

hashicorp_vault_cli = {
    "enabled": False,
}

php_development = {
    "enabled": False,
    # renovate: datasource=github-tags depName=php/php-src
    "php_version": "8.4.10",
}

openwebui = {
    "enabled": True,
    "BRAVE_API_KEY": "",
    "extra_env": {
        "ENABLE_OPENAI_API": "true",
        "OPENAI_API_BASE_URL": "http://aisix:3000/v1",
        "DEFAULT_MODELS": "chat,chat_thinking,web_research,translate_de,translate_en,fix_grammar_en,fix_grammar_de,linux_cli",
        "ENABLE_API_KEYS": "true",
    },
    # Set in local.py — written into the openwebui .env (mode 600)
    "opencode_api_key": "",
    "opencode_api_key_2": "",
    "opencode_api_key_3": "",
    "requesty_api_key": "",
    "cortecs_api_key": "",
    "openwebui_caller_key": "",
    "opencode_base_url": "https://opencode.ai/zen/v1",
    "requesty_base_url": "https://router.requesty.ai/v1",
    "cortecs_base_url": "https://api.cortecs.ai/v1",
    "zen_model_chat": "deepseek-v4-flash",
    "zen_model_chat_thinking": "deepseek-v4-pro",
    "zen_model_web_research": "qwen3.8-flash",
    "zen_model_fast": "mimo-v2.6-flash",
    "requesty_model_chat": "novita/deepseek/deepseek-v3.2",
    "cortecs_model_chat": "glm-5.3-flash",
}

vagrant = {
    "enabled": False,
}

ubuntu_cleanup = {
    "enabled": True,
}


def __load_local_overrides(override_file: str) -> None:
    import importlib.util

    def _deep_merge(base: dict, override: dict) -> dict:  # type: ignore[type-arg]
        result = dict(base)
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = _deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    local_path = os.path.join(os.path.dirname(str(__file__)), override_file)
    if not os.path.exists(local_path):
        return

    spec = importlib.util.spec_from_file_location("_local_overrides", local_path)
    if spec is None or spec.loader is None:
        return
    local_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(local_mod)

    g = globals()
    for key in [k for k in vars(local_mod) if not k.startswith("_")]:
        val = getattr(local_mod, key)
        if key in g and isinstance(g[key], dict) and isinstance(val, dict):
            g[key] = _deep_merge(g[key], val)
        else:
            g[key] = val


if os.getenv("CI"):
    __load_local_overrides("ci.py")
__load_local_overrides("local.py")
