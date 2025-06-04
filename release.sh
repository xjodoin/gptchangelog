#!/bin/bash

# Release automation script for gptchangelog
# This script generates changelog, updates version, commits, tags, and deploys

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# Function to check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository. Please run this script from the project root."
        exit 1
    fi
}

# Function to check if working directory is clean
check_clean_working_dir() {
    if ! git diff-index --quiet HEAD --; then
        log_error "Working directory is not clean. Please commit or stash your changes."
        git status --porcelain
        exit 1
    fi
}

# Function to get current version
get_current_version() {
    grep -o "__version__ = '[^']*'" gptchangelog/__init__.py | sed "s/__version__ = '//" | sed "s/'//"
}

# Function to validate version format (semantic versioning)
validate_version() {
    local version=$1
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_error "Invalid version format. Please use semantic versioning (e.g., 1.2.3)"
        return 1
    fi
    return 0
}

# Function to update version in __init__.py
update_version() {
    local new_version=$1
    local current_date=$(date +%Y-%m-%d)
    
    log_step "Updating version to $new_version in gptchangelog/__init__.py"
    
    # Create backup
    cp gptchangelog/__init__.py gptchangelog/__init__.py.backup
    
    # Update version and date
    sed -i.tmp "s/__version__ = '[^']*'/__version__ = '$new_version'/" gptchangelog/__init__.py
    sed -i.tmp "s/__date__ = '[^']*'/__date__ = '$current_date'/" gptchangelog/__init__.py
    
    # Remove temporary file (macOS compatibility)
    rm -f gptchangelog/__init__.py.tmp
    
    log_success "Version updated to $new_version"
}

# Function to generate changelog and extract next version
generate_changelog_and_version() {
    log_step "Generating changelog and extracting next version using gptchangelog..."
    
    # Check if gptchangelog is available
    if ! command -v gptchangelog &> /dev/null; then
        log_warning "gptchangelog not found in PATH. Installing in development mode..."
        pip install -e .
    fi
    
    # Create temporary file to capture output
    local temp_output=$(mktemp)
    
    # Generate changelog with enhanced mode and quality analysis, capture output
    if ! gptchangelog generate --dry-run --quality-analysis --stats > "$temp_output" 2>&1; then
        log_error "Failed to generate changelog"
        cat "$temp_output"
        rm -f "$temp_output"
        return 1
    fi
    
    # Extract the next version from the output
    # Look for "Next version: X.Y.Z" pattern
    local suggested_version=$(grep -o "Next version: [0-9]\+\.[0-9]\+\.[0-9]\+" "$temp_output" | sed 's/Next version: //')
    
    if [[ -z "$suggested_version" ]]; then
        log_error "Could not extract next version from gptchangelog output"
        log_info "Full output:"
        cat "$temp_output"
        rm -f "$temp_output"
        return 1
    fi
    
    # Clean up temp file
    rm -f "$temp_output"
    
    # Set the extracted version
    SUGGESTED_VERSION="$suggested_version"
    
    log_success "Suggested next version: $SUGGESTED_VERSION"
    
    # Now generate the actual changelog interactively
    log_step "Generating final changelog interactively..."
    if ! gptchangelog generate --interactive --quality-analysis --stats; then
        log_error "Failed to generate final changelog"
        return 1
    fi
    
    log_success "Changelog generated successfully"
}

# Function to commit changes
commit_changes() {
    local version=$1
    local commit_message="Release version $version

- Updated version to $version
- Generated changelog
- Updated release date"
    
    log_step "Committing changes..."
    
    git add CHANGELOG.md gptchangelog/__init__.py
    git commit -m "$commit_message"
    
    log_success "Changes committed"
}

# Function to create git tag
create_tag() {
    local version=$1
    local tag_name="v$version"
    
    log_step "Creating git tag $tag_name..."
    
    git tag -a "$tag_name" -m "Release version $version"
    
    log_success "Git tag $tag_name created"
}

# Function to deploy to PyPI
deploy_to_pypi() {
    log_step "Deploying to PyPI..."
    
    if [[ ! -f "deploy.sh" ]]; then
        log_error "deploy.sh script not found"
        return 1
    fi
    
    # Make deploy script executable
    chmod +x deploy.sh
    
    # Run deployment
    if ! ./deploy.sh; then
        log_error "Deployment failed"
        return 1
    fi
    
    log_success "Successfully deployed to PyPI"
}

# Function to push to remote repository
push_to_remote() {
    local version=$1
    
    log_step "Pushing changes and tags to remote repository..."
    
    # Push commits
    git push origin
    
    # Push tags
    git push origin "v$version"
    
    log_success "Changes and tags pushed to remote repository"
}

# Function to display pre-release summary
show_release_summary() {
    local current_version=$1
    local new_version=$2
    
    echo -e "\n${CYAN}============================================${NC}"
    echo -e "${CYAN}           RELEASE SUMMARY${NC}"
    echo -e "${CYAN}============================================${NC}"
    echo -e "Project: ${YELLOW}gptchangelog${NC}"
    echo -e "Current version: ${RED}$current_version${NC}"
    echo -e "New version: ${GREEN}$new_version${NC}"
    echo -e "Release date: ${BLUE}$(date +%Y-%m-%d)${NC}"
    echo -e "Git branch: ${YELLOW}$(git branch --show-current)${NC}"
    echo -e "Git status: ${GREEN}Clean${NC}"
    echo -e "${CYAN}============================================${NC}\n"
}

# Function to rollback changes on failure
rollback_changes() {
    local version=$1
    
    log_warning "Rolling back changes..."
    
    # Restore backup if it exists
    if [[ -f "gptchangelog/__init__.py.backup" ]]; then
        mv gptchangelog/__init__.py.backup gptchangelog/__init__.py
        log_info "Restored original __init__.py"
    fi
    
    # Reset any staged changes
    git reset HEAD -- . 2>/dev/null || true
    
    # Remove tag if it was created
    if git tag -l "v$version" | grep -q "v$version"; then
        git tag -d "v$version"
        log_info "Removed git tag v$version"
    fi
    
    log_warning "Rollback completed"
}

# Main function
main() {
    log_info "Starting gptchangelog release process..."
    
    # Pre-flight checks
    check_git_repo
    check_clean_working_dir
    
    # Get current version
    current_version=$(get_current_version)
    log_info "Current version: $current_version"
    
    # Step 1: Generate changelog and extract suggested version
    if ! generate_changelog_and_version; then
        log_error "Failed to generate changelog and extract version"
        exit 1
    fi
    
    # Use the automatically suggested version
    new_version="$SUGGESTED_VERSION"
    
    # Validate extracted version
    if ! validate_version "$new_version"; then
        log_error "Generated version '$new_version' is not valid"
        exit 1
    fi
    
    # Check if version is different from current
    if [[ "$new_version" == "$current_version" ]]; then
        log_warning "Generated version ($new_version) is the same as current version"
        echo -e "${YELLOW}Would you like to override with a custom version? (y/N):${NC}"
        read -p "" -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "\n${YELLOW}Please enter the new version number (current: $current_version):${NC}"
            read -p "New version: " custom_version
            
            if ! validate_version "$custom_version"; then
                exit 1
            fi
            
            if [[ "$custom_version" == "$current_version" ]]; then
                log_error "Custom version must be different from current version"
                exit 1
            fi
            
            new_version="$custom_version"
        else
            log_info "Keeping suggested version and proceeding"
        fi
    fi
    
    # Show release summary
    show_release_summary "$current_version" "$new_version"
    
    # Final confirmation
    echo -e "${YELLOW}This will:${NC}"
    echo "1. Use the generated changelog (already created)"
    echo "2. Update version to $new_version"
    echo "3. Commit the changes" 
    echo "4. Create git tag v$new_version"
    echo "5. Push to remote repository"
    echo "6. Deploy to PyPI"
    echo ""
    
    read -p "Do you want to proceed? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Release cancelled by user"
        exit 0
    fi
    
    # Execute release steps with error handling
    trap 'rollback_changes "$new_version"; exit 1' ERR
    
    log_info "Starting release process..."
    
    # Step 2: Update version
    update_version "$new_version"
    
    # Step 3: Commit changes
    commit_changes "$new_version"
    
    # Step 4: Create tag
    create_tag "$new_version"
    
    # Step 5: Push to remote
    push_to_remote "$new_version"
    
    # Step 6: Deploy to PyPI
    deploy_to_pypi
    
    # Cleanup
    rm -f gptchangelog/__init__.py.backup
    
    # Success message
    echo -e "\n${GREEN}============================================${NC}"
    echo -e "${GREEN}       RELEASE COMPLETED SUCCESSFULLY!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo -e "Version ${GREEN}$new_version${NC} has been:"
    echo -e "✅ Changelog generated and committed"
    echo -e "✅ Version updated and committed"
    echo -e "✅ Git tag ${GREEN}v$new_version${NC} created"
    echo -e "✅ Changes pushed to remote repository"
    echo -e "✅ Package deployed to PyPI"
    echo -e "\nYou can now:"
    echo -e "• Check the release on GitHub: ${BLUE}https://github.com/xjodoin/gptchangelog/releases${NC}"
    echo -e "• Install the new version: ${YELLOW}pip install --upgrade gptchangelog${NC}"
    echo -e "${GREEN}============================================${NC}\n"
    
    log_success "Release process completed successfully!"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
