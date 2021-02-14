from subprocess import Popen, PIPE
import os

PATH = os.getcwd()

items = os.listdir(os.getcwd())


def check_file(py_file):
    print(f"Checking {py_file}...")
    process = Popen(["python", "-m", "pyflakes", py_file], 
                        stdout=PIPE, stderr=PIPE)
    for line in iter(process.stdout.readline, b""):
        print(line.decode("utf-8"))
    process.wait()

for item in items:
    if os.path.isfile(item):
        if item.endswith(".py"):
            check_file(item)
    elif os.path.isdir(item):
        nextpath = os.path.join(PATH, item)
        for nextitem in os.listdir(nextpath):
            nextpathitem = os.path.join(nextpath, nextitem)
            if os.path.isfile(nextpathitem):
                if nextpathitem.endswith('.py'):
                    check_file(nextpathitem)
            

input("Press return to exit")