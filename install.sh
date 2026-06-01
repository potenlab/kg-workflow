#!/usr/bin/env bash
# kg-workflow installer for non-Claude-Code platforms.
#
# Claude Code users should install via:
#   /plugin marketplace add potenlab/kg-workflow
#   /plugin install kg-workflow
#
# Usage:
#   ./install.sh                       Prompt for platform
#   ./install.sh <platform>            Install for <platform>
#   ./install.sh --update              Pull latest changes
#   ./install.sh --uninstall <plat>    Remove links for <plat>
#   ./install.sh --help
#
# Curl-pipe usage:
#   curl -fsSL https://raw.githubusercontent.com/potenlab/kg-workflow/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/potenlab/kg-workflow/main/install.sh | bash -s codex
#
# Environment:
#   KG_REPO_URL  Override clone URL  (default: official GitHub repo)
#   KG_DIR       Override clone destination  (default: $HOME/.kg-workflow/repo)

set -euo pipefail

REPO_URL="${KG_REPO_URL:-https://github.com/potenlab/kg-workflow.git}"
REPO_DIR="${KG_DIR:-$HOME/.kg-workflow/repo}"

platforms_table() {
  cat <<EOF
gemini|$HOME/.agents/skills|per-skill
codex|$HOME/.agents/skills|per-skill
opencode|$HOME/.agents/skills|per-skill
vibe|$HOME/.vibe/skills|per-skill
vscode|$HOME/.copilot/skills|per-skill
EOF
}

platform_ids() { platforms_table | cut -d'|' -f1; }

resolve_platform() {
  local id="$1"
  local row
  row="$(platforms_table | awk -F'|' -v id="$id" '$1==id {print; exit}')"
  if [[ -z "$row" ]]; then
    printf 'Unknown platform: %s\n' "$id" >&2
    printf 'Supported: %s\n' "$(platform_ids | tr '\n' ' ')" >&2
    exit 1
  fi
  printf '%s\n' "$row"
}

prompt_platform() {
  local ids=()
  while IFS= read -r id; do ids+=("$id"); done < <(platform_ids)

  printf 'Which platform are you installing for?\n' >&2
  local i=1
  for id in "${ids[@]}"; do
    printf '  %d) %s\n' "$i" "$id" >&2
    i=$((i+1))
  done
  printf 'Choose [1-%d]: ' "${#ids[@]}" >&2

  local choice=""
  if { exec 3</dev/tty; } 2>/dev/null; then
    read -r choice <&3 || true
    exec 3<&-
  else
    read -r choice || true
  fi
  if [[ -z "$choice" ]]; then
    printf '\nNo input received. Pass the platform as an argument, e.g.:\n' >&2
    printf '  install.sh codex\n' >&2
    exit 1
  fi
  if ! [[ "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice > ${#ids[@]} )); then
    printf 'Invalid choice: %s\n' "$choice" >&2
    exit 1
  fi
  printf '%s\n' "${ids[$((choice-1))]}"
}

clone_or_update() {
  if [[ -d "$REPO_DIR/.git" ]]; then
    printf -- '→ Updating existing checkout at %s\n' "$REPO_DIR"
    git -C "$REPO_DIR" pull --ff-only
  else
    printf -- '→ Cloning %s → %s\n' "$REPO_URL" "$REPO_DIR"
    mkdir -p "$(dirname "$REPO_DIR")"
    git clone "$REPO_URL" "$REPO_DIR"
  fi
}

skills_root() { printf '%s\n' "$REPO_DIR/kg-workflow-plugin/skills"; }

list_skills() {
  local root
  root="$(skills_root)"
  if [[ ! -d "$root" ]]; then
    printf 'Skills directory not found: %s\n' "$root" >&2
    exit 1
  fi
  local d
  for d in "$root"/*/; do
    [[ -d "$d" ]] || continue
    basename "$d"
  done
}

link_skills() {
  local target="$1" style="$2"
  local root
  root="$(skills_root)"
  mkdir -p "$target"
  case "$style" in
    per-skill)
      local skill
      while IFS= read -r skill; do
        ln -sfn "$root/$skill" "$target/$skill"
        printf '  ✓ %s → %s\n' "$target/$skill" "$root/$skill"
      done < <(list_skills)
      ;;
    *)
      printf 'Unsupported link style: %s\n' "$style" >&2
      exit 1
      ;;
  esac
}

unlink_skills() {
  local target="$1" style="$2"
  case "$style" in
    per-skill)
      local skill
      while IFS= read -r skill; do
        if [[ -L "$target/$skill" ]]; then
          rm "$target/$skill"
          printf '  ✗ %s\n' "$target/$skill"
        fi
      done < <(list_skills)
      ;;
  esac
}

usage() {
  cat <<USAGE
kg-workflow installer

Usage:
  install.sh [<platform>]            Install for <platform> (or prompt if omitted)
  install.sh --update                Pull latest changes (skills update via symlink)
  install.sh --uninstall <platform>  Remove links for <platform>
  install.sh --help

Supported platforms:
$(platform_ids | sed 's/^/  - /')

Note: Claude Code users should install via the marketplace, not this script:
  /plugin marketplace add potenlab/kg-workflow
  /plugin install kg-workflow

Environment:
  KG_REPO_URL  Override clone URL (default: official repo)
  KG_DIR       Override clone destination (default: \$HOME/.kg-workflow/repo)
USAGE
}

main() {
  case "${1:-}" in
    -h|--help)
      usage
      ;;
    --update)
      if [[ ! -d "$REPO_DIR/.git" ]]; then
        printf 'No existing checkout at %s. Run install.sh first.\n' "$REPO_DIR" >&2
        exit 1
      fi
      git -C "$REPO_DIR" pull --ff-only
      ;;
    --uninstall)
      local platform="${2:-}"
      if [[ -z "$platform" ]]; then
        printf 'Usage: install.sh --uninstall <platform>\n' >&2
        exit 1
      fi
      local row target style
      row="$(resolve_platform "$platform")"
      target="$(printf '%s\n' "$row" | cut -d'|' -f2)"
      style="$(printf '%s\n' "$row" | cut -d'|' -f3)"
      unlink_skills "$target" "$style"
      ;;
    "")
      local platform
      platform="$(prompt_platform)"
      clone_or_update
      local row target style
      row="$(resolve_platform "$platform")"
      target="$(printf '%s\n' "$row" | cut -d'|' -f2)"
      style="$(printf '%s\n' "$row" | cut -d'|' -f3)"
      link_skills "$target" "$style"
      printf 'Installed kg-workflow skills for %s. Restart your CLI.\n' "$platform"
      ;;
    *)
      local platform="$1"
      clone_or_update
      local row target style
      row="$(resolve_platform "$platform")"
      target="$(printf '%s\n' "$row" | cut -d'|' -f2)"
      style="$(printf '%s\n' "$row" | cut -d'|' -f3)"
      link_skills "$target" "$style"
      printf 'Installed kg-workflow skills for %s. Restart your CLI.\n' "$platform"
      ;;
  esac
}

main "$@"
