"""Packaging metadata. Installing this project never runs pip recursively."""

from setuptools import find_packages, setup

setup(
    name="astra-jarvis-assistant",
    version="0.2.0",
    description="Local desktop assistant powered by OpenJarvis and Ollama",
    packages=find_packages(exclude=("tests", "tests.*")),
    include_package_data=True,
)
