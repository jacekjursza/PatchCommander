"""
Build script for PatchCommander.
Creates executable files for Windows, macOS, and Linux using PyInstaller.
"""
import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path
import time

def run_command(command, cwd=None):
    """Run a command and return its output."""
    print(f'Executing: {command}')
    if isinstance(command, str):
        cmd_args = command.split()
    else:
        cmd_args = command
    try:
        process = subprocess.run(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, cwd=cwd)
        if process.stdout:
            print(process.stdout)
        if process.returncode != 0:
            print(f'Error executing command (return code {process.returncode})')
            if process.stderr:
                print(f'STDERR: {process.stderr}')
            return False
        return True
    except Exception as e:
        print(f'Exception while executing command: {e}')
        return False

def build_executable():
    """Build executable for the current platform."""
    system = platform.system().lower()

    if os.path.exists('build'):
        print('Removing previous build directory...')
        shutil.rmtree('build')

    if os.path.exists('dist'):
        print('Cleaning executable files from dist directory...')
        executable_files = []
        for file in os.listdir('dist'):
            if not file.endswith('.whl') and (not file.endswith('.tar.gz')):
                file_path = os.path.join('dist', file)
                if os.path.isfile(file_path):
                    executable_files.append(file_path)

        for file_path in executable_files:
            print(f'Removing {file_path}...')
            os.remove(file_path)

    print('Installing required packages...')
    run_command([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    run_command([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

    spec_file = f'pcmd_{system}.spec'

    try:
        if not os.path.exists('resources/icon.ico') or not os.path.exists('resources/icon.icns') or (not os.path.exists('resources/icon.png')):
            print('Generating basic icons...')
            if os.path.exists('generate_icons.py'):
                run_command([sys.executable, 'generate_icons.py'])
            else:
                print('Icon generator script not found. Proceeding without icons.')

        if os.path.exists(spec_file):
            print(f'Building from existing spec file: {spec_file}')
            success = run_command([sys.executable, '-m', 'PyInstaller', spec_file])
        else:
            print('Creating new PyInstaller configuration...')
            cmd = [
                sys.executable, '-m', 'PyInstaller',
                '--name=pcmd',
                '--onefile',
                '--clean',
                '--noconfirm',
                'cli.py'
            ]

            cmd.extend([
                '--hidden-import=rich.console',
                '--hidden-import=rich.syntax',
                '--hidden-import=rich.panel',
                '--hidden-import=rich.prompt',
                '--hidden-import=rich.markdown',
                '--hidden-import=tree_sitter',
                '--hidden-import=tree_sitter_python',
                '--hidden-import=tree_sitter_javascript'
            ])

            if os.path.exists('LICENSE'):
                data_sep = ';' if system == 'windows' else ':'
                cmd.append(f'--add-data=LICENSE{data_sep}.')

            if os.path.exists('PROMPT.md'):
                data_sep = ';' if system == 'windows' else ':'
                cmd.append(f'--add-data=PROMPT.md{data_sep}.')

            if os.path.exists('FOR_LLM.md'):
                data_sep = ';' if system == 'windows' else ':'
                cmd.append(f'--add-data=FOR_LLM.md{data_sep}.')

            if system == 'windows':
                if os.path.exists('resources/icon.ico'):
                    cmd.append('--icon=resources/icon.ico')
                    cmd.append('--add-data=resources/icon.ico;resources')
            elif system == 'darwin':
                if os.path.exists('resources/icon.icns'):
                    cmd.append('--icon=resources/icon.icns')
                    cmd.append('--add-data=resources/icon.icns:resources')
            elif system == 'linux':
                if os.path.exists('resources/icon.png'):
                    cmd.append('--add-data=resources/icon.png:resources')

            print('Running PyInstaller...')
            success = run_command(cmd)

            if success:
                time.sleep(1)
                spec_files = list(Path('.').glob('*.spec'))
                if spec_files:
                    try:
                        os.rename(spec_files[0], spec_file)
                        print(f'Created spec file: {spec_file}')
                    except Exception as e:
                        print(f'Could not rename spec file: {e}')

        if success:
            print('\nBuild completed successfully!')
            exe_path = Path('dist/pcmd')
            if system == 'windows':
                exe_path = Path('dist/pcmd.exe')
            print(f'Executable created at: {exe_path.absolute()}')
        else:
            print('\nBuild failed!')

    except Exception as e:
        print(f'Error during build process: {e}')
        import traceback
        traceback.print_exc()
        return False

    return success

if __name__ == '__main__':
    print(f'PatchCommander Build Script - Running on {platform.system()}')
    print('=' * 60)

    if not os.path.exists('resources'):
        os.makedirs('resources')

    try:
        success = build_executable()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print('\nBuild cancelled by user.')
        sys.exit(130)
    except Exception as e:
        print(f'\nUnexpected error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)