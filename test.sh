#!/usr/bin/env bash

###
Rules Recap

If PROFILE is given:

Case A: Branch exists in mapping and matches with input profile → return profile.

Case B: Branch & profile both exist in mapping but do not match → return empty.

Case C: Branch and profile both do not exist in mapping → return given profile (no warning).

Case D: Branch has no mapping, and profile not listed in mapping → return given profile (no warning).

If PROFILE is empty:

Case E: Branch exists in mapping → return first profile match.

Case F: Branch does not exist in mapping → return empty.
###

YAML_FILE="env-mapping.yaml"
BRANCH="$1"
PROFILE="$2"
TARGET=""

# --- FUNCTIONS ---

try_yq() {
    if command -v yq >/dev/null 2>&1; then
        yq "$@" 2>/dev/null || return 1
    else
        return 1
    fi
}

# Get profiles for branch
get_profiles_by_branch() {
    local branch="$1"
    if try_yq -r --arg b "$branch" '.["env-mapping"] | to_entries[] | select(.value[] == $b) | .key' "$YAML_FILE"; then
        return
    fi
    awk -v b="$branch" '
        BEGIN{profile=""}
        /^[[:space:]]*[a-zA-Z0-9_-]+:/ {gsub(":",""); profile=$1}
        $1 == "-" && $2 == b {print profile}
    ' "$YAML_FILE"
}

# Get branches for profile
get_branches_by_profile() {
    local profile="$1"
    if try_yq -r --arg p "$profile" '.["env-mapping"][$p][]?' "$YAML_FILE"; then
        return
    fi
    awk -v p="$profile" '
        $0 ~ "^ *"p":" {in_profile=1; next}
        /^[[:space:]]*[a-zA-Z0-9_-]+:/ {in_profile=0}
        in_profile && $1 == "-" {print $2}
    ' "$YAML_FILE"
}

# Check if profile exists in mapping
profile_exists_in_mapping() {
    local profile="$1"
    if try_yq -r --arg p "$profile" '.["env-mapping"] | has($p)' "$YAML_FILE"; then
        return
    fi
    awk -v p="$profile" '
        /^[[:space:]]*[a-zA-Z0-9_-]+:/ {gsub(":",""); if ($1 == p) found=1}
        END{exit !found}
    ' "$YAML_FILE"
}

# --- MAIN LOGIC ---
if [[ -n "$PROFILE" ]]; then
    branch_profiles=$(get_profiles_by_branch "$BRANCH")

    if [[ -n "$branch_profiles" ]]; then
        # Branch exists in mapping
        if echo "$branch_profiles" | grep -Fx "$PROFILE" >/dev/null 2>&1; then
            # Case A
            TARGET="$PROFILE"
        fi
    else
        # Branch not in mapping
        if profile_exists_in_mapping "$PROFILE"; then
            # Profile exists in mapping → branch not in mapping, return empty
            echo ""
        else
            # Case C & D
            TARGET="$PROFILE"
        fi
    fi
else
    # PROFILE is empty
    detected_profiles=$(get_profiles_by_branch "$BRANCH")
    if [[ -n "$detected_profiles" ]]; then
        # Case E
		TARGET=$(echo "$detected_profiles" | head -n 1)
    fi
fi

echo 'Mapped env=$TARGET'
