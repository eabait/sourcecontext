# sourcecontext

## Introduction

**sourcecontext** is a Python script that traverses the structure of a project folder (typically a Git-managed repository) and generates a comprehensive text file containing:

1. **An ASCII tree** of the project’s directories and files.  
2. **The contents of each file**, preceded by its relative path.

By respecting your project’s `.gitignore` rules (in a simplified manner) and excluding default files like `.DS_Store` and `.gitignore` itself, **sourcecontext** helps create a clean snapshot of your codebase.

## Usage

### Prerequisites

- **Python 3.x** installed on your system.

### Steps

1. **Download** (or copy) the script file `sourcecontext.py` into a desired location on your machine.
2. **Open a Terminal** (or Command Prompt) in the same directory where `sourcecontext.py` resides.
3. **Run** the following command:

   ```bash
   python sourcecontext.py <input_folder> <output_file>
   ```
- <input_folder>: The root directory of your project.
- <output_file>: The path (and filename) of the text file you want to generate.
#### Example
```bash
python sourcecontext.py /Users/johndoe/MyProject /Users/johndoe/output_sourcecontext.txt
```
1. The script will read and parse .gitignore (if it exists in MyProject).
2. It will skip ignored files/directories as well as .DS_Store, .gitignore, and any folders listed in SKIP_DIRS (like .git).
3. The output file (output_sourcecontext.txt in this example) will contain the ASCII tree of non-ignored files, followed by the contents of each included file.

# How It Works
1. Parsing .gitignore
    - sourcecontext loads .gitignore patterns from <input_folder>/.gitignore.
    - It also has a set of default ignores (.gitignore itself and .DS_Store) which are always excluded.

2. Traverse the File Tree
    - The script walks through <input_folder> recursively.
    - It skips:
        - Folders hardcoded in SKIP_DIRS (e.g., .git).
        - Any file or folder matching the .gitignore patterns.
        - The output file if it’s located within <input_folder> and not excluded by .gitignore.

3. Generate ASCII Structure
- The script builds an ASCII tree, similar to the Unix tree command.
- Ignored paths do not appear in the tree.

4. Dump File Contents
- For each non-ignored file, the script writes its relative path (from the project root) and then prints the file’s contents.
- The final output file includes:
    **PROJECT STRUCTURE**: The ASCII tree of all included directories and files.
    **FILE CONTENTS**: The textual content of each included file.

5. Progress Messages
- While running, sourcecontext logs progress messages to the terminal (e.g., how many ignore patterns are loaded, each file being processed, etc.).

# Limitations
While sourcecontext is effective for basic project exports, there are some caveats:

1. Simplified .gitignore Parsing
- The script uses Python’s fnmatch for pattern matching, which does not fully replicate Git’s .gitignore (negations like !pattern, nested .gitignore files, etc. are not supported).
- Advanced or complex patterns may not be handled exactly as Git does.

2. Performance on Large Codebases
- For projects with thousands of files, the script may be slow. Progress logging for each file can introduce additional overhead.

3. Encoding Assumptions
- Files are opened with UTF-8 and errors="replace". Non-UTF-8 or binary files may produce garbled text or unreadable output in the final export.

4. Single .gitignore Scope
- sourcecontext only checks the .gitignore located at the root of <input_folder>.
- It does not support nested .gitignore files in subdirectories.

5. Output File Placement
- If <output_file> is placed inside <input_folder> and not ignored by .gitignore, the script may attempt to process it unless it is specifically excluded.
- It’s often best to place the output file outside the source folder or add it to .gitignore.
---
sourcecontext provides a convenient way to share, document, or back up a snapshot of your code while respecting project ignore rules and excluding unwanted files. If you encounter edge cases or need advanced .gitignore handling, consider extending the script or integrating a library that fully implements Git’s ignore logic.