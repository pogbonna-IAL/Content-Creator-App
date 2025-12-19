"""
Setup script as fallback for package installation
"""
from setuptools import setup, find_packages

setup(
    name="content_creation_crew",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.10,<3.14",
)

