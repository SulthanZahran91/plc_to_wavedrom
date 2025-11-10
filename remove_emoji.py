#!/usr/bin/env python3
"""Script to remove all emoji from source files and documentation."""

import re
from pathlib import Path

# List of files to process
FILES_TO_PROCESS = [
    "test_data/TEST_SCENARIO_GUIDE.md",
    "python_plc_visualizer/test_validator.py",
    "python_plc_visualizer/scripts/test_chunked_loading_quick.py",
    "python_plc_visualizer/scripts/test_chunked_loading.py",
    "python_plc_visualizer/plc_visualizer/utils/chunk_manager.py",
    "python_plc_visualizer/plc_visualizer/ui/views/home_view.py",
    "python_plc_visualizer/plc_visualizer/ui/main_window.py",
    "python_plc_visualizer/plc_visualizer/ui/dialogs/help_dialog.py",
    "python_plc_visualizer/plc_visualizer/ui/components/stats_widget.py",
    "python_plc_visualizer/plc_visualizer/ui/components/file_list_widget.py",
    "python_plc_visualizer/plc_visualizer/ui/components/file_upload_widget.py",
    "python_plc_visualizer/plc_visualizer/models/chunked_log.py",
    "TESTING_CHECKLIST.md",
    ".cursor/plans/fix-timing-0c9e7857.plan.md",
]

def remove_emoji(text):
    """Remove emoji from text using regex pattern for common emoji ranges."""
    # Pattern to match most emoji
    emoji_pattern = re.compile(
        "["
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"
        "\u2600-\u26FF"          # Miscellaneous Symbols
        "\u2700-\u27BF"          # Dingbats
        "\u2B50"                 # Star
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)

def process_file(file_path):
    """Process a single file to remove emoji."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove emoji
        new_content = remove_emoji(content)

        # Only write if content changed
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✓ Processed: {file_path}")
            return True
        else:
            print(f"- No changes: {file_path}")
            return False
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False

def main():
    """Main entry point."""
    repo_root = Path(__file__).parent

    print("Removing emoji from files...")
    print("=" * 60)

    processed_count = 0
    for file_path in FILES_TO_PROCESS:
        full_path = repo_root / file_path
        if full_path.exists():
            if process_file(full_path):
                processed_count += 1
        else:
            print(f"✗ File not found: {file_path}")

    print("=" * 60)
    print(f"Processed {processed_count} file(s) with changes")

if __name__ == "__main__":
    main()
