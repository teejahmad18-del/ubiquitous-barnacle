import os
import fnmatch
import re

def load_gitignore_patterns(project_root):
    """
    Load patterns from .gitignore file if it exists.
    Returns a list of patterns.
    """
    gitignore_path = os.path.join(project_root, '.gitignore')
    patterns = []
    
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    patterns.append(line)
    
    return patterns

def should_exclude(filepath, project_root, gitignore_patterns):
    """
    Check if a file should be excluded based on gitignore patterns and common exclusions.
    """
    # Convert to relative path for gitignore matching
    rel_path = os.path.relpath(filepath, project_root).replace('\\', '/')
    filename = os.path.basename(filepath)
    
    # Check against gitignore patterns
    for pattern in gitignore_patterns:
        # Handle directory patterns (ending with /)
        if pattern.endswith('/'):
            pattern = pattern[:-1]
            if pattern in rel_path or fnmatch.fnmatch(rel_path, f"*{pattern}*"):
                return True
        # Handle file patterns
        elif fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel_path, pattern):
            return True
    
    # Common exclusions for Django projects
    exclude_paths = [
        '__pycache__',
        '.pyc',
        '.pyo',
        'migrations/',
        'venv/',
        'env/',
        '.env',
        '.venv/',
        'node_modules/',
        '.git/',
        '.idea/',
        '.vscode/',
    ]
    
    for exclude in exclude_paths:
        if exclude in rel_path.replace('\\', '/'):
            return True
    
    # Exclude specific files
    exclude_files = [
        '__init__.py',  # Usually empty, comment out if needed
        'settings.py',  # Contains sensitive data
        'wsgi.py',
        'asgi.py',
        'manage.py',    # Standard boilerplate
    ]
    
    if filename in exclude_files:
        return True
    
    return False

def combine_python_files(project_root, output_file='combine.txt'):
    """
    Combine all Python files in the Django project into a single text file.
    """
    gitignore_patterns = load_gitignore_patterns(project_root)
    
    python_files = []
    
    # Walk through the project directory
    for root, dirs, files in os.walk(project_root):
        # Skip directories that are commonly excluded
        dirs_to_remove = set()
        for d in dirs:
            if d in ['__pycache__', '.git', 'venv', 'env', '.venv', 'node_modules', '.idea', '.vscode', 'migrations']:
                dirs_to_remove.add(d)
        dirs[:] = [d for d in dirs if d not in dirs_to_remove]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                
                # Skip if should be excluded
                if not should_exclude(filepath, project_root, gitignore_patterns):
                    python_files.append(filepath)
    
    # Sort files for consistent output
    python_files.sort()
    
    # Write combined file
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write("=" * 80 + "\n")
        outfile.write("DJANGO PROJECT COMBINED PYTHON FILES\n")
        outfile.write(f"Project Root: {project_root}\n")
        outfile.write(f"Total Files: {len(python_files)}\n")
        outfile.write("=" * 80 + "\n\n")
        
        for i, filepath in enumerate(python_files, 1):
            rel_path = os.path.relpath(filepath, project_root)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                
                # Skip empty files (optional)
                if not content.strip():
                    print(f"[{i}/{len(python_files)}] Skipped (empty): {rel_path}")
                    continue
                
                # Write file separator and header
                outfile.write("\n" + "=" * 80 + "\n")
                outfile.write(f"# File {i}/{len(python_files)}\n")
                outfile.write(f"# Path: {rel_path}\n")
                outfile.write(f"# Full Path: {filepath}\n")
                outfile.write("=" * 80 + "\n\n")
                
                # Write file content
                outfile.write(content)
                outfile.write("\n\n")
                
                print(f"[{i}/{len(python_files)}] Added: {rel_path}")
                
            except Exception as e:
                outfile.write(f"\n# ERROR: Could not read file: {rel_path}\n")
                outfile.write(f"# Error: {str(e)}\n\n")
                print(f"Error reading {rel_path}: {e}")
    
    print(f"\n✓ Successfully combined {len(python_files)} Python files into {output_file}")
    return len(python_files)

if __name__ == "__main__":
    # Set your project root path
    PROJECT_ROOT = r"C:\Users\Lenovo Thinkpad X390\Music\tradingbot\tradingbot"
    
    # Output file path (will be created in the project root)
    output_path = os.path.join(PROJECT_ROOT, 'combine.txt')
    
    # Run the combination
    combine_python_files(PROJECT_ROOT, output_path)
    
    print(f"Output file created at: {output_path}")