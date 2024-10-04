import os
import re
import click
import toml

def filter_files(files, include, exclude):
    if include:
        files = [f for f in files if any(f.endswith(ext) for ext in include)]
    if exclude:
        files = [f for f in files if not any(f.endswith(ext) for ext in exclude)]
    return files

def get_project_name(directory):
    # Check for pyproject.toml
    pyproject_path = os.path.join(directory, 'pyproject.toml')
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, 'r') as f:
                pyproject = toml.load(f)
                if 'project' in pyproject and 'name' in pyproject['project']:
                    return pyproject['project']['name']
        except (toml.TomlDecodeError, KeyError) as e:
            click.echo(f"Warning: Could not parse pyproject.toml - {e}", err=True)

    # Check for README files
    readme_files = [f for f in os.listdir(directory) if re.match(r'README(\.\w+)?$', f, re.IGNORECASE)]
    if readme_files:
        with open(os.path.join(directory, readme_files[0]), 'r') as f:
            first_line = f.readline().strip()
            if first_line.startswith('# '):
                return first_line[2:]

    # Fallback to directory name
    return os.path.basename(os.path.abspath(directory))

def get_git_repo_name(directory):
    git_path = os.path.join(directory, '.git', 'config')
    if os.path.exists(git_path):
        with open(git_path, 'r') as f:
            for line in f:
                if line.strip().startswith('url = '):
                    if '=' in line:
                        repo_url = line.split('=', 1)[1].strip()
                        return repo_url.split('/')[-1].replace('.git', '')
    return None

@click.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, readable=True), default='.')
@click.option('--include', '-i', multiple=True, default=['.py', '.ts', '.js', '.go', '.rust', '.h', '.c', '.cpp', '.conf'], help='Only include files with these extensions (default: .py, .ts, .js, .go, .rust, .h, .c, .cpp, .conf)')
@click.option('--exclude', '-e', multiple=True, help='Exclude files with these extensions (e.g. .pyc, .log)')
@click.option('--max-depth', '-d', type=int, default=None, help='Max depth to traverse in the directory tree')
@click.option('--output', '-o', type=click.File('w'), default='-', help='Output file to save the result (default is stdout)')
def generate_tree(directory, include, exclude, max_depth, output):
    """
    Generate a tree view of the given DIRECTORY (defaults to current directory if not provided), optionally filtering by file type.
    """
    # Get project name
    project_name = get_project_name(directory)
    git_repo_name = get_git_repo_name(directory)
    project_title = git_repo_name if git_repo_name else project_name

    click.echo(f"Project: {project_title}\n", file=output)

    click.echo("<filetree>", file=output)
    for root, dirs, files in os.walk(directory, topdown=True):
        depth = root[len(directory):].count(os.sep)
        if max_depth is not None and depth >= max_depth:
            # Prevent further traversal by clearing dirs
            dirs[:] = []
            continue

        indent = '  ' * depth
        click.echo(f"{indent}{os.path.basename(root)}/", file=output)

        # Filter files once per directory
        files = filter_files(files, include, exclude)
        for f in files:
            click.echo(f"{indent}  {f}", file=output)
    click.echo("</filetree>\n", file=output)

    # List included files
    click.echo("---\nIncluded files:\n", file=output)
    for ext in include:
        click.echo(f"`{ext}`", file=output)

if __name__ == '__main__':
    generate_tree()
