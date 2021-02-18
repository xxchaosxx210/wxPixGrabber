from subprocess import Popen, PIPE
import os
import argparse
import logging
from functools import partial

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
_Log = logging.getLogger()

PATH = os.getcwd()

def check_file(py_file):
    """uses pyflake to scan for errors and warnings in the py_file

    Args:
        py_file (str): The path of the python file to check
    """
    print(f"Checking {py_file}...")
    process = Popen(["python", "-m", "pyflakes", py_file], 
                        stdout=PIPE, stderr=PIPE)
    for line in iter(process.stdout.readline, b""):
        _Log.info(line.decode("utf-8"))
    process.wait()

def check_paths(project_path):
    """iters through root path and checks each python file for issues using pyflake

    Args:
        project_path (str): The root directory to start looking for py files
    """
    for pyfile in iter(get_py_files(project_path)):
        check_file(pyfile)

def get_py_files(project_path):
    """searches for folders found in project_path and lists py files

    Args:
        project_path (str): is the root path to start looking for python files in

    Returns:
        list: returns full path to the python files found
    """
    pyfiles_found = []
    for item in iter(os.listdir(project_path)):
        if os.path.isfile(item):
            if item.endswith(".py"):
                pyfiles_found.append(os.path.join(project_path, item))
        elif os.path.isdir(item):
            nextpath = os.path.join(PATH, item)
            for nextitem in os.listdir(nextpath):
                nextpathitem = os.path.join(nextpath, nextitem)
                if os.path.isfile(nextpathitem):
                    if nextpathitem.endswith('.py'):
                        pyfiles_found.append(nextpathitem)
    return pyfiles_found

def grep_search(keywords):
    """Loops through python files in PATH and searches for keyword match in line

    Args:
        keywords (str): Keywords to search
    """
    print_border = partial(print, "-"*100)
    print_border()
    for pyfile in iter(sorted(get_py_files(PATH))):
        matches_found = 0
        with open(pyfile) as fp:
            lines = fp.read().split("\n")
            for index, line in enumerate(lines):
                if keywords in line:
                    _Log.info(f"Found match in {pyfile} on Line {index}")
                    matches_found += 1
            if matches_found:
                print_border()

def _main():
    parser = argparse.ArgumentParser(description="Check py files for errors. Also does a basic Grep search for words.")
    parser.add_argument("--check", "-c", 
    help="Use pyflakes to check through the py files", action="store_true"
    )
    parser.add_argument("--grep", "-g", help=\
        "Scans each file looking for keyword returns filename and line number if match",
        nargs="+", type=str)

    namespace = parser.parse_args()
    if namespace.grep:
        grep_search(" ".join(namespace.grep))
    elif namespace.check:
        check_paths(PATH)
    else:
        print(parser.format_help())

if __name__ == '__main__':
    _main()