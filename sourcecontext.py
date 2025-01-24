#!/usr/bin/env python3

import os
import sys
import fnmatch
import argparse
import logging
from typing import List, Set, Generator

# A hardcoded set of directories we always skip, even if not in .gitignore
SKIP_DIRS: Set[str] = {".git"}

# Default ignore patterns: always ignore these files at any level
DEFAULT_IGNORES: List[str] = [
    ".DS_Store",
    ".gitignore"
]

def setup_logging() -> None:
    """Set up logging configuration."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate context for an LLM to do coding tasks.")
    parser.add_argument("input_folder", help="Path to the input folder")
    parser.add_argument("output_file", help="Path to the output file")
    return parser.parse_args()

def preprocess_gitignore_pattern(pattern: str) -> List[str]:
    """
    Convert a single .gitignore line (or default ignore entry) into one or more
    fnmatch patterns that approximate Git's directory/file ignores at any level.

    Args:
        pattern (str): The pattern from .gitignore or default ignores.

    Returns:
        List[str]: List of fnmatch patterns.
    """
    pattern = pattern.strip()
    if not pattern or pattern.startswith('#'):
        return []

    # If the pattern ends with '/', it's a directory
    if pattern.endswith('/'):
        dir_name = pattern[:-1]  # remove trailing slash
        if '/' not in dir_name:
            # e.g., "env/" => 4 patterns to catch top-level or deeper "env" folders
            return [
                dir_name,           # top-level env
                f"{dir_name}/*",    # contents of top-level env
                f"*/{dir_name}",    # env at deeper levels
                f"*/{dir_name}/*"   # contents of deeper env
            ]
        else:
            # e.g., "src/env/" => just "src/env" and "src/env/*"
            return [dir_name, f"{dir_name}/*"]
    else:
        # It's a file pattern (no trailing slash)
        # If there's no slash at all, prefix with "*/" so it matches anywhere
        if '/' not in pattern:
            return [f"*/{pattern}", pattern]  # Match at any level and root level
        else:
            # e.g., "foo/bar.txt" => leave as is
            return [pattern]

def load_gitignore_patterns(gitignore_path: str) -> List[str]:
    """
    Read .gitignore file (if present) and transform each non-empty,
    non-comment line into fnmatch patterns.

    Args:
        gitignore_path (str): Path to the .gitignore file.

    Returns:
        List[str]: List of fnmatch patterns.
    """
    all_patterns: List[str] = []
    if os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comment lines
                    if not line or line.startswith('#'):
                        continue
                    converted = preprocess_gitignore_pattern(line)
                    all_patterns.extend(converted)
        except Exception as e:
            logging.warning(f"Failed to read .gitignore file: {e}")
    return all_patterns

def matches_gitignore(path_rel: str, ignore_patterns: List[str]) -> bool:
    """
    Check if 'path_rel' (relative path) matches any pattern in 'ignore_patterns'.

    Args:
        path_rel (str): Relative path to check.
        ignore_patterns (List[str]): List of fnmatch patterns.

    Returns:
        bool: True if the path matches any pattern, False otherwise.
    """
    path_rel = path_rel.replace('\\', '/')
    for pat in ignore_patterns:
        pat = pat.replace('\\', '/')
        if fnmatch.fnmatch(path_rel, pat):
            return True
    return False

def sort_entries(entries: List[str]) -> List[str]:
    """
    Sort entries so that:
      1) README.md (exact name match) is first among files
      2) other files in alphabetical order
      3) directories in alphabetical order

    Args:
        entries (List[str]): List of file and directory paths.

    Returns:
        List[str]: Sorted list of entries.
    """
    files = [e for e in entries if os.path.isfile(e)]
    dirs = [e for e in entries if os.path.isdir(e)]

    files_sorted = sorted(files, key=lambda x: (os.path.basename(x) != "README.md", x.lower()))
    dirs_sorted = sorted(dirs, key=lambda x: x.lower())
    return files_sorted + dirs_sorted

def generate_tree_lines(root_path: str, output_file: str, ignore_patterns: List[str], prefix: str = "") -> Generator[str, None, None]:
    """
    Recursively generate lines for the ASCII tree.

    Args:
        root_path (str): Root directory to start from.
        output_file (str): Path to the output file (to avoid including it).
        ignore_patterns (List[str]): List of fnmatch patterns to ignore.
        prefix (str): Prefix for tree indentation.

    Yields:
        str: Lines of the ASCII tree.
    """
    try:
        child_names = os.listdir(root_path)
    except OSError as e:
        logging.warning(f"Failed to list directory {root_path}: {e}")
        return

    entries = []
    for name in child_names:
        path = os.path.join(root_path, name)

        # Skip any dir in SKIP_DIRS by exact name
        if name in SKIP_DIRS:
            continue

        # Skip if it's the output file
        if os.path.abspath(path) == os.path.abspath(output_file):
            continue

        # Check if it matches .gitignore / default ignores
        from_repo_root = os.path.relpath(path, start=root_path)
        if matches_gitignore(from_repo_root, ignore_patterns):
            continue

        entries.append(path)

    # Sort them (README first among files, then other files, then dirs)
    entries = sort_entries(entries)
    count = len(entries)

    for i, child_path in enumerate(entries):
        base_name = os.path.basename(child_path)
        is_last = (i == count - 1)
        branch_symbol = "└── " if is_last else "├── "

        yield prefix + branch_symbol + base_name

        if os.path.isdir(child_path):
            new_prefix = prefix + ("    " if is_last else "│   ")
            yield from generate_tree_lines(child_path, output_file, ignore_patterns, prefix=new_prefix)

def gather_all_files(root_path: str, output_file: str, ignore_patterns: List[str]) -> List[str]:
    """
    Recursively gather all files under 'root_path', skipping ignored items.

    Args:
        root_path (str): Root directory to start from.
        output_file (str): Path to the output file (to avoid including it).
        ignore_patterns (List[str]): List of fnmatch patterns to ignore.

    Returns:
        List[str]: List of file paths to include.
    """
    all_files = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Remove directories in SKIP_DIRS
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        # Also remove dirs that match .gitignore / default patterns
        new_dirnames = []
        for d in dirnames:
            full_dpath = os.path.join(dirpath, d)
            from_repo_root = os.path.relpath(full_dpath, start=root_path)
            if not matches_gitignore(from_repo_root, ignore_patterns):
                new_dirnames.append(d)
        dirnames[:] = new_dirnames

        # Now check each file
        for f in filenames:
            file_path = os.path.join(dirpath, f)

            # Skip the output file
            if os.path.abspath(file_path) == os.path.abspath(output_file):
                continue

            # Check if it matches ignore patterns
            from_repo_root = os.path.relpath(file_path, start=root_path)
            if matches_gitignore(from_repo_root, ignore_patterns):
                continue

            all_files.append(file_path)

    return sorted(all_files, key=lambda x: x.lower())

def write_output(output_file: str, input_folder: str, tree_lines: List[str], files_list: List[str]) -> None:
    """
    Write the generated context to the output file.

    Args:
        output_file (str): Path to the output file.
        input_folder (str): Path to the input folder.
        tree_lines (List[str]): Lines of the ASCII tree.
        files_list (List[str]): List of file paths to include.
    """
    try:
        with open(output_file, "w", encoding="utf-8") as outfile:
            # The tree
            outfile.write("PROJECT STRUCTURE:\n")
            outfile.write("===================\n")
            outfile.write(f"{input_folder}\n")
            for line in tree_lines:
                outfile.write(line + "\n")

            # The file contents
            outfile.write("\n\nFILE CONTENTS:\n")
            outfile.write("===================\n")

            total_files = len(files_list)
            for i, fpath in enumerate(files_list, start=1):
                rel_path = os.path.relpath(fpath, input_folder)
                logging.info(f"[{i}/{total_files}] Reading file: {rel_path}")
                outfile.write(f"=== PATH: {rel_path} ===\n")
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    outfile.write(content)
                except Exception as e:
                    outfile.write(f"[Could not read file content: {e}]\n")
                outfile.write("\n\n")
    except Exception as e:
        logging.error(f"Failed to write output file: {e}")
        sys.exit(1)

def main() -> None:
    """Main function to generate the context."""
    setup_logging()
    args = parse_arguments()
    input_folder = os.path.abspath(args.input_folder)
    output_file = os.path.abspath(args.output_file)

    if not os.path.isdir(input_folder):
        logging.error(f"Input folder does not exist: {input_folder}")
        sys.exit(1)

    logging.info("Loading .gitignore patterns...")
    ignore_patterns = load_gitignore_patterns(os.path.join(input_folder, ".gitignore"))

    # Add default ignore patterns
    for ignore in DEFAULT_IGNORES:
        ignore_patterns.extend(preprocess_gitignore_pattern(ignore))

    logging.info(f"Loaded {len(ignore_patterns)} total ignore pattern(s).")

    logging.info("Generating ASCII tree (skipping ignored items)...")
    tree_lines = list(generate_tree_lines(input_folder, output_file, ignore_patterns))
    logging.info(f"Generated {len(tree_lines)} lines of structure.")

    logging.info("Gathering file list (skipping ignored items)...")
    files_list = gather_all_files(input_folder, output_file, ignore_patterns)
    logging.info(f"Found {len(files_list)} files to include.\n")

    logging.info(f"Writing results to '{output_file}'...\n")
    write_output(output_file, input_folder, tree_lines, files_list)

    logging.info(f"\nDone! Output written to '{output_file}'.\n")

if __name__ == "__main__":
    main()