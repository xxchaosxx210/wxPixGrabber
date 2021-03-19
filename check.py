from subprocess import Popen, PIPE
import os
import argparse
import logging
import re
from functools import partial

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
_Log = logging.getLogger()

PATH = os.getcwd()
PYTHON_EXT = re.compile(r'^.+?(\.py|\.pyw|\.pyx)$')


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
    for py_file in iter(get_py_files(project_path)):
        check_file(py_file)


def get_py_files(project_path):
    """searches for folders found in project_path and lists py files

    Args:
        project_path (str): is the root path to start looking for python files in

    Returns:
        list: returns full path to the python files found
    """
    found_files = []
    for root, dir_names, file_names in os.walk(project_path):
        for file_name in file_names:
            if PYTHON_EXT.search(file_name):
                found_files.append(os.path.join(root, file_name))
    return found_files


def grep_search(keywords):
    """Loops through python files in PATH and searches for keyword match in line

    Args:
        keywords (str): Keywords to search
    """
    print_border = partial(print, "-" * 100)
    print_border()
    for py_file in iter(sorted(get_py_files(PATH))):
        matches_found = 0
        with open(py_file) as fp:
            lines = fp.read().split("\n")
            for index, line in enumerate(lines):
                if keywords in line:
                    _Log.info(f"Found match in {py_file} on Line {index+1}")
                    matches_found += 1
            if matches_found:
                print_border()


def _main():
    parser = argparse.ArgumentParser(description="Check py files for errors. Also does a basic Grep search for words.")
    parser.add_argument("--check", "-c",
                        help="Use pyflakes to check through the py files", action="store_true")
    parser.add_argument("--grep", "-g", help= \
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
