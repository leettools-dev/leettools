#!/bin/bash

# Script to format changed files according to VS Code settings
# Supports Python files (.py), Markdown files (.md), and Bash scripts (.sh)
# Checks diff against dev branch and formats all modified files
#
# Usage:
#   ./scripts/format-diff.sh                    # Interactive mode (asks for confirmation)
#   ./scripts/format-diff.sh --yes              # Auto-format without confirmation
#   ./scripts/format-diff.sh -y                 # Same as --yes
#   ./scripts/format-diff.sh --file <path>      # Format specific file
#   ./scripts/format-diff.sh -f <path>          # Same as --file
#   ./scripts/format-diff.sh --dir <path>       # Format all Python files in directory
#   ./scripts/format-diff.sh -d <path>          # Same as --dir
#   ./scripts/format-diff.sh -f file.py --yes  # Combine options
#
# Formatting applied:
#   Python files (.py):
#     - Black formatter with line-length 100 (if available)
#     - Ruff formatting and import organization
#     - Trailing whitespace removal
#   Markdown (.md) and Bash (.sh) files:
#     - Trailing whitespace removal
#     - Empty line cleanup
#   - Follows .vscode/settings.json configuration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command-line arguments
SPECIFIC_FILE=""
SPECIFIC_DIR=""
AUTO_YES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --file|-f)
            SPECIFIC_FILE="$2"
            shift 2
            ;;
        --dir|-d)
            SPECIFIC_DIR="$2"
            shift 2
            ;;
        --yes|-y)
            AUTO_YES=true
            shift
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo -e "${BLUE}Usage: $0 [--file|-f <path>] [--dir|-d <path>] [--yes|-y]${NC}"
            exit 1
            ;;
    esac
done

# Display current formatting configuration
echo -e "${BLUE}📋 Formatting Configuration:${NC}"

# Function to extract value from JSON (simplified)
get_vscode_setting() {
    local key="$1"
    local file=".vscode/settings.json"
    if [ -f "$file" ]; then
        grep -o "\"$key\"[[:space:]]*:[[:space:]]*[^,}]*" "$file" 2>/dev/null | sed 's/.*:[[:space:]]*//' | tr -d '"[]' | head -1
    fi
}

# Function to extract value from TOML
get_toml_setting() {
    local section="$1"
    local key="$2"  
    local file="pyproject.toml"
    if [ -f "$file" ]; then
        awk -v section="[$section]" -v key="$key" '
        $0 == section {in_section=1; next}
        /^\[/ && in_section {in_section=0}
        in_section && $0 ~ "^" key "[[:space:]]*=" {
            gsub(/^[^=]*=[[:space:]]*/, "")
            gsub(/^"/, ""); gsub(/"$/, "")
            print
            exit
        }' "$file" 2>/dev/null
    fi
}

# Read Black configuration
BLACK_LINE_LENGTH=""
if [ -f ".vscode/settings.json" ]; then
    VSCODE_BLACK_ARGS=$(get_vscode_setting "black-formatter.args")
    if echo "$VSCODE_BLACK_ARGS" | grep -q "line-length"; then
        BLACK_LINE_LENGTH=$(echo "$VSCODE_BLACK_ARGS" | grep -o '[0-9]\+' | head -1)
    fi
fi

if [ -z "$BLACK_LINE_LENGTH" ] && [ -f "pyproject.toml" ]; then
    BLACK_LINE_LENGTH=$(get_toml_setting "tool.black" "line-length")
fi

# Set default if not found
BLACK_LINE_LENGTH=${BLACK_LINE_LENGTH:-88}

# Display configuration
echo -e "  ${GREEN}Black formatter:${NC}"
echo -e "    Line length: ${YELLOW}${BLACK_LINE_LENGTH}${NC}"
if [ -f ".vscode/settings.json" ]; then
    echo -e "    Source: ${BLUE}.vscode/settings.json${NC} (black-formatter.args)"
elif [ -f "pyproject.toml" ]; then
    echo -e "    Source: ${BLUE}pyproject.toml${NC} ([tool.black] line-length)"
else
    echo -e "    Source: ${YELLOW}default${NC}"
fi

echo -e "  ${GREEN}Ruff:${NC}"
if command -v ruff >/dev/null 2>&1; then
    echo -e "    Status: ${GREEN}available${NC}"
    RUFF_VERSION=$(ruff --version 2>/dev/null | head -1 || echo "unknown")
    echo -e "    Version: ${YELLOW}${RUFF_VERSION}${NC}"
else
    echo -e "    Status: ${RED}not available${NC}"
fi

echo -e "  ${GREEN}File types supported:${NC}"
echo -e "    Python (.py): ${YELLOW}Black + Ruff + whitespace cleanup${NC}"
echo -e "    Markdown (.md): ${YELLOW}whitespace cleanup + empty line removal${NC}"
echo -e "    Bash (.sh): ${YELLOW}whitespace cleanup + empty line removal${NC}"

echo -e "  ${GREEN}Configuration files:${NC}"
[ -f ".vscode/settings.json" ] && echo -e "    ${GREEN}✓${NC} .vscode/settings.json found" || echo -e "    ${RED}✗${NC} .vscode/settings.json not found"
[ -f "pyproject.toml" ] && echo -e "    ${GREEN}✓${NC} pyproject.toml found" || echo -e "    ${RED}✗${NC} pyproject.toml not found"

echo ""

# Collect files to format based on options
if [[ -n "$SPECIFIC_FILE" ]]; then
    echo -e "${BLUE}🎯 Formatting specific file: $SPECIFIC_FILE${NC}"

    # Validate file exists and is a Python file
    if [[ ! -f "$SPECIFIC_FILE" ]]; then
        echo -e "${RED}❌ File not found: $SPECIFIC_FILE${NC}"
        exit 1
    fi

    if [[ ! "$SPECIFIC_FILE" == *.py && ! "$SPECIFIC_FILE" == *.md && ! "$SPECIFIC_FILE" == *.sh ]]; then
        echo -e "${RED}❌ File must be a Python (.py), Markdown (.md), or Bash (.sh) file: $SPECIFIC_FILE${NC}"
        exit 1
    fi

    ALL_FILES="$SPECIFIC_FILE"
elif [[ -n "$SPECIFIC_DIR" ]]; then
    echo -e "${BLUE}🎯 Formatting files in directory: $SPECIFIC_DIR${NC}"

    # Validate directory exists
    if [[ ! -d "$SPECIFIC_DIR" ]]; then
        echo -e "${RED}❌ Directory not found: $SPECIFIC_DIR${NC}"
        exit 1
    fi

    # Find all supported files in the directory recursively
    ALL_FILES=$(find "$SPECIFIC_DIR" \( -name "*.py" -o -name "*.md" -o -name "*.sh" \) -type f 2>/dev/null | sort || true)

    if [[ -z "$ALL_FILES" ]]; then
        echo -e "${RED}❌ No Python (.py), Markdown (.md), or Bash (.sh) files found in directory: $SPECIFIC_DIR${NC}"
        exit 1
    fi
else
    echo -e "${BLUE}🔍 Checking for changed files against dev branch...${NC}"

    # Get list of changed files compared to dev branch
    CHANGED_FILES=$(git diff dev...HEAD --name-only --diff-filter=AM | grep -E '\.(py|md|sh)$' || true)

    # Also check for locally modified files not yet committed
    LOCAL_FILES=$(git status --porcelain | grep -E '^[ M].*\.(py|md|sh)$' | awk '{print $2}' || true)

    # Combine and deduplicate files
    ALL_FILES=$(echo -e "$CHANGED_FILES\n$LOCAL_FILES" | sort -u | grep -v '^$' || true)
fi

if [ -z "$ALL_FILES" ]; then
    echo -e "${GREEN}✅ No files to format${NC}"
    exit 0
fi

echo -e "${YELLOW}📝 Found files to format:${NC}"
echo "$ALL_FILES" | while read -r file; do
    echo "  - $file"
done

# Check if running in interactive mode or with --yes flag
if [[ "$AUTO_YES" == true ]]; then
    echo -e "${GREEN}✅ Auto-formatting enabled${NC}"
else
    echo ""
    read -p "Do you want to format these files? (y/N): " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}⏭️  Formatting cancelled${NC}"
        exit 0
    fi
fi

echo -e "${BLUE}🔧 Formatting files...${NC}"

# Format each file
FORMATTED_COUNT=0
ERROR_COUNT=0

while IFS= read -r file; do
    if [ -f "$file" ]; then
        echo -e "${BLUE}Formatting: $file${NC}"

        # Determine file type and apply appropriate formatting
        if [[ "$file" == *.py ]]; then
            # Python file - apply full formatting

            # Check if Black is available, otherwise use Ruff format
            if command -v black >/dev/null 2>&1; then
                # Apply Black formatting with detected line length
                if black --line-length "$BLACK_LINE_LENGTH" "$file" 2>/dev/null; then
                    echo -e "  ${GREEN}✅ Black formatting applied${NC}"
                else
                    echo -e "  ${RED}❌ Black formatting failed${NC}"
                    ((ERROR_COUNT++))
                    continue
                fi
            else
                echo -e "  ${YELLOW}⚠️  Black not available, using Ruff format${NC}"
            fi

            # Apply ruff formatting and organize imports
            if ruff format "$file" 2>/dev/null; then
                echo -e "  ${GREEN}✅ Ruff formatting applied${NC}"
            else
                echo -e "  ${YELLOW}⚠️  Ruff format skipped (not available or failed)${NC}"
            fi

            # Fix imports and other issues with ruff
            if ruff check --fix "$file" 2>/dev/null; then
                echo -e "  ${GREEN}✅ Import organization applied${NC}"
            else
                echo -e "  ${YELLOW}⚠️  Ruff check/fix skipped (not available or failed)${NC}"
            fi

        elif [[ "$file" == *.md || "$file" == *.sh ]]; then
            # Markdown or Bash file - only whitespace cleanup
            echo -e "  ${BLUE}📝 Applying whitespace cleanup for ${file##*.} file${NC}"
        fi

        # Remove trailing whitespace (applied to all file types)
        if sed -i '' 's/[[:space:]]*$//' "$file" 2>/dev/null; then
            echo -e "  ${GREEN}✅ Trailing whitespace removed${NC}"
        else
            echo -e "  ${YELLOW}⚠️  Trailing whitespace removal failed${NC}"
        fi

        # Remove excessive empty lines for markdown and bash files
        if [[ "$file" == *.md || "$file" == *.sh ]]; then
            # Remove multiple consecutive empty lines, keeping max 2
            if sed -i '' '/^$/N;/^\n$/d' "$file" 2>/dev/null; then
                echo -e "  ${GREEN}✅ Empty line cleanup applied${NC}"
            else
                echo -e "  ${YELLOW}⚠️  Empty line cleanup failed${NC}"
            fi
        fi

        ((FORMATTED_COUNT++))
        echo ""
    else
        echo -e "${RED}❌ File not found: $file${NC}"
        ((ERROR_COUNT++))
    fi
done <<< "$ALL_FILES"

echo -e "${GREEN}🎉 Formatting complete!${NC}"
echo -e "Files processed: $FORMATTED_COUNT"
if [ $ERROR_COUNT -gt 0 ]; then
    echo -e "${RED}Errors: $ERROR_COUNT${NC}"
fi

echo ""
echo -e "${BLUE}💡 To see what changed, run:${NC}"
echo "  git diff"