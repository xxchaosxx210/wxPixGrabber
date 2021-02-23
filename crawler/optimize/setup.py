from setuptools import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

ext = Extension("constants", sources=["constants.pyx"])

setup(ext_modules=[ext], cmdclass={"build_ext": build_ext})