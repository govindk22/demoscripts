#!/usr/bin/env bash

YAML_FILE="env-mapping.yml"

# Try yq, fall back to awk silently
try_yq() {
    if command -v yq >/dev/null 2>&1; then
        yq "$@" 2>/dev/null || return 1
    else
        return 1
    fi
}

# Get profile for a given branch
get_profile_by_branch() {
    local branch="$1"
    if try_yq -r --arg b "$branch" '.["env-mapping"] | to_entries[] | select(.value[] == $b) | .key' "$YAML_FILE"; then
        return
    fi
    awk -v b="$branch" '
        BEGIN{profile=""}
        /^[[:space:]]*[a-zA-Z0-9_-]+:/ {gsub(":",""); profile=$1}
        $0 ~ b {print profile}
    ' "$YAML_FILE"
}

# Get all branches for a given profile
get_branches_by_profile() {
    local profile="$1"
    if try_yq -r --arg p "$profile" '.["env-mapping"][$p][]?' "$YAML_FILE"; then
        return
    fi
    awk -v p="$profile" '
        $0 ~ "^ *"p":" {in_profile=1; next}
        /^[[:space:]]*[a-zA-Z0-9_-]+:/ {in_profile=0}
        in_profile && NF {gsub("- ",""); print}
    ' "$YAML_FILE"
}

# --- MAIN LOGIC ---

if [[ -n "$PROFILE" ]]; then
    branch_profiles=$(get_profile_by_branch "$BRANCH")

    if [[ -n "$branch_profiles" ]]; then
        # Branch exists in mapping
        if [[ "$PROFILE" == "$branch_profiles" ]]; then
            echo "$PROFILE"
        else
            echo "Warning: Profile '$PROFILE' does not match mapping for branch '$BRANCH'. Setting profile empty." >&2
            echo ""
        fi
    else
        # Branch not in mapping → keep given profile
        echo "$PROFILE"
    fi
else
    # Profile not provided
    detected_profile=$(get_profile_by_branch "$BRANCH")
    echo "${detected_profile:-}"
fi
