#!/bin/bash

# =======================================================
# Custom Packages Git Clone Script for Release Build
# =======================================================

if [ -z "$GITHUB_WORKSPACE" ]; then
    echo "❌ Error: GITHUB_WORKSPACE is not set!"
    exit 1
fi

CUSTOM_PKG_DIR="$GITHUB_WORKSPACE/openwrt-sdk/package/custom_packages"
RELEASE_NOTES="$GITHUB_WORKSPACE/release_notes.txt"

mkdir -p "$CUSTOM_PKG_DIR"
> "$RELEASE_NOTES"

echo "### 📦 编译包含的插件源码 (Included Upstream Sources)" >> "$RELEASE_NOTES"
echo "" >> "$RELEASE_NOTES"

# ---------------------------------------------------
# 📦 Configuration 1: Full Repositories
# ---------------------------------------------------
declare -A FULL_REPOS
FULL_REPOS=(

)

# ---------------------------------------------------
# 📂 Configuration 2: Sparse Checkout
# ---------------------------------------------------
SPARSE_REPOS=(
    "immortalwrt/packages|openwrt-25.12|net/ua2f"
    "immortalwrt/luci|openwrt-25.12|applications/luci-app-ua2f applications/luci-app-arpbind"
)

if [ "$1" == "--check" ]; then
    echo "🔍 Check mode initiated: Scanning configuration arrays..."
    if [ ${#FULL_REPOS[@]} -eq 0 ] && [ ${#SPARSE_REPOS[@]} -eq 0 ]; then
        echo "⚠️ Result: Arrays are empty. No plugins to compile."
        echo "has_plugins=false" >> "$GITHUB_OUTPUT"
    else
        echo "✅ Result: Plugins found. Proceeding with subsequent steps."
        echo "has_plugins=true" >> "$GITHUB_OUTPUT"
    fi
    exit 0 # Check complete, exiting script without executing clone logic
fi

# =======================================================
# 🚦 Empty Array Interceptor for Normal Execution (Safety Check)
# =======================================================
if [ ${#FULL_REPOS[@]} -eq 0 ] && [ ${#SPARSE_REPOS[@]} -eq 0 ]; then
    echo "⚠️ Notice: No repositories configured for synchronization (lists are empty or fully commented out)."
    echo "💤 Script exiting safely. Skipping subsequent clone and build steps."
    echo "- No plugins configured. Compilation has been skipped." >> "$RELEASE_NOTES"
    exit 0
fi
echo "---------------------------------------------------"
echo "📦 Phase 1: Cloning full repositories"
echo "---------------------------------------------------"
for repo in "${!FULL_REPOS[@]}"; do
    branch="${FULL_REPOS[$repo]}"
    folder_name=$(basename "$repo" .git) 
    target_path="$CUSTOM_PKG_DIR/$folder_name"
    
    echo "📥 Cloning: $folder_name"
    if [ -z "$branch" ]; then
        git clone --depth 1 "$repo" "$target_path" >/dev/null 2>&1
    else
        git clone --depth 1 -b "$branch" "$repo" "$target_path" >/dev/null 2>&1
    fi
    
    if [ $? -eq 0 ]; then
        pushd "$target_path" >/dev/null
        commit_hash=$(git rev-parse --short HEAD)
        popd >/dev/null
        echo "- **$folder_name**: \`$repo\` @ \`$commit_hash\`" >> "$RELEASE_NOTES"
    else
        echo "❌ Clone failed for $folder_name"
    fi
done

echo ""
echo "---------------------------------------------------"
echo "📂 Phase 2: Cloning specific subdirectories"
echo "---------------------------------------------------"
for entry in "${SPARSE_REPOS[@]}"; do
    entry=$(echo "$entry" | tr -d '\r\n')
    IFS='|' read -r repo branch sub_dirs <<< "$entry"
    
    repo_url="https://github.com/${repo}.git"
    tmp_dir=$(mktemp -d)
    
    branch_args=()
    [ -n "$branch" ] && branch_args=("-b" "$branch")
    
    echo "📥 Sparse cloning from: $repo"
    git clone --filter=blob:none --no-checkout "${branch_args[@]}" "$repo_url" "$tmp_dir" >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        pushd "$tmp_dir" >/dev/null
        dirs_array=($sub_dirs)
        git sparse-checkout set "${dirs_array[@]}" >/dev/null 2>&1
        git checkout >/dev/null 2>&1
        
        for sub_dir in "${dirs_array[@]}"; do
            target_name=$(basename "$sub_dir") # 核心：只提取最后的目录名 (如 ua2f)
            target_path="$CUSTOM_PKG_DIR/$target_name"
            
            if [ -d "$sub_dir" ]; then
                mv "$sub_dir" "$target_path"
                commit_hash=$(git log -1 --format="%h" -- "$sub_dir")
                echo "- **$target_name**: \`$repo_url\` ($sub_dir) @ \`$commit_hash\`" >> "$RELEASE_NOTES"
                echo "✅ Extracted: $target_name"
            fi
        done
        popd >/dev/null
    else
        echo "❌ Sparse clone metadata failed for $repo"
    fi
    rm -rf "$tmp_dir"
done

echo ""
echo "---------------------------------------------------"
echo "🔧 Phase 3: Fixing luci.mk include paths"
echo "---------------------------------------------------"


find "$CUSTOM_PKG_DIR" -name Makefile -type f | while read -r makefile; do
    if grep -q "include ../../luci.mk" "$makefile"; then
        sed -i 's|include \.\./\.\./luci\.mk|include $(TOPDIR)/feeds/luci/luci.mk|g' "$makefile"
        
        pkg_name=$(basename "$(dirname "$makefile")")
        echo "🛠️ Fixed luci.mk path in: $pkg_name"
    fi
done

echo "🎉 All custom packages cloned and patched successfully!"

