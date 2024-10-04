import os
import re
import click
import toml
import fnmatch
import scandir

def filter_files(files, include, exclude):
    if include:
        files = [f for f in files if any(fnmatch.fnmatch(f, pattern) for pattern in include)]
    if exclude:
        files = [f for f in files if not any(fnmatch.fnmatch(f, pattern) for pattern in exclude)]
    return files

def get_project_name(directory):
    pyproject_path = os.path.join(directory, 'pyproject.toml')
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, 'r') as f:
                pyproject = toml.load(f)
                if 'project' in pyproject and 'name' in pyproject['project']:
                    return pyproject['project']['name']
        except (toml.TomlDecodeError, KeyError, OSError):
            pass

    readme_files = [f for f in os.listdir(directory) if re.match(r'(?i)^README(\.\w+)?$', f)]
    if readme_files:
        with open(os.path.join(directory, readme_files[0]), 'r') as f:
            first_line = f.readline().strip()
            if first_line.startswith('# '):
                return first_line[2:]

    return os.path.basename(os.path.abspath(directory))

def get_git_repo_name(directory):
    git_path = os.path.join(directory, '.git', 'config')
    if os.path.exists(git_path):
        with open(git_path, 'r') as f:
            for line in f:
                if line.strip().startswith('url = '):
                    repo_url = line.split('=', 1)[1].strip()
                    return repo_url.split('/')[-1].replace('.git', '')
    return None

def check_max_depth(depth, max_depth, dirs):
    if max_depth is not None and depth >= max_depth:
        dirs[:] = []

def collect_included_files(directory, include, exclude, max_depth):
    included_files = []
    for root, dirs, files in scandir.walk(directory, topdown=True):
        depth = root[len(directory):].count(os.sep)
        check_max_depth(depth, max_depth, dirs)

        dirs[:] = [d for d in dirs if not d.startswith('.') and not any(fnmatch.fnmatch(os.path.join(root, d), pattern) for pattern in exclude)]
        files = [f for f in files if not f.startswith('.') and not any(fnmatch.fnmatch(os.path.join(root, f), pattern) for pattern in exclude)]

        files = filter_files(files, include, exclude)
        for f in files:
            included_files.append(os.path.join(root, f))
    return included_files

@click.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, readable=True), default='.')
@click.option('--include', '-i', multiple=True, default=['README*', '*.py', '*.ts', '*.js', '*.go', '*.rust', '*.h', '*.c', '*.cpp', '*.conf'], help='Only include files matching these patterns (default: *.py, *.ts, *.js, *.go, *.rust, *.h, *.c, *.cpp, *.conf)')
@click.option('--exclude', '-e', multiple=True, help='Exclude files matching these patterns (e.g. *.pyc, *.log)')
@click.option('--max-depth', '-d', type=int, default=None, help='Max depth to traverse in the directory tree')
@click.option('--output', '-o', type=click.File('w'), default='-', help='Output file to save the result (default is stdout)')
@click.option('--instructions', '-t', type=str, default="This is relevant code from the our project repository. If CANVAS or ARTIFACT functionality is available, create one named for each file and output the content, then acknowledge that we are ready to begin work on these files. If the functionality is not available, simply acknowledge that you are ready to begin work on these files.", help='Custom instructions to include at the end of the output')
def generate_tree(directory, include, exclude, max_depth, output, instructions):
    project_name = get_project_name(directory)
    git_repo_name = get_git_repo_name(directory)
    project_title = git_repo_name if git_repo_name else project_name

    click.echo(f"Project: {project_title}\n", file=output)

    click.echo("<filetree>", file=output)
    for root, dirs, files in scandir.walk(directory, topdown=True):
        depth = root[len(directory):].count(os.sep)
        check_max_depth(depth, max_depth, dirs)

        dirs[:] = [d for d in dirs if not d.startswith('.')]

        indent = '  ' * depth
        click.echo(f"{indent}{os.path.basename(root)}/", file=output)

        all_files = [f for f in files if not f.startswith('.')]
        for f in all_files:
            click.echo(f"{indent}  {f}", file=output)
    click.echo("</filetree>", file=output)

    included_files = collect_included_files(directory, include, exclude, max_depth)

    readme_files = [f for f in included_files if re.match(r'(?i).*/README(\.\w+)?$', f)]
    included_files = sorted(included_files, key=lambda x: (x not in readme_files, x))

    click.echo("\n---\n", file=output)
    for file in included_files:
        click.echo(f"`{file}`\n", file=output)
        click.echo("```", file=output)
        try:
            with open(file, 'r') as f:
                click.echo(f.read(), file=output)
        except Exception as e:
            click.echo(f"Error reading file {file}: {e}", file=output)
        click.echo("```\n", file=output)

    add_instructions(output, instructions)

def add_instructions(output, instructions):
    click.echo("---\n", file=output)
    click.echo(instructions, file=output)

if __name__ == '__main__':
    generate_tree()
