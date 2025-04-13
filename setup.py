import os
import re
from setuptools import setup, find_packages

# Get package version without importing the package
with open(os.path.join("damascus", "__init__.py"), "r") as f:
    content = f.read()
    version_match = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', content, re.M)
    if not version_match:
        raise RuntimeError("Unable to find version string.")
    version = version_match.group(1)

# Read README.md for the long description
with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="damascus",
    version=version,
    description="SDK generator for OpenAPI specifications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Beshu Limited",
    author_email="info@beshu.tech",
    url="https://github.com/beshu-tech/damascus",
    packages=find_packages(exclude=["tests", "examples"]),
    install_requires=[
        "requests==2.32.3",
        "urllib3==2.4.0",
        "jinja2==3.1.6",
        "pyyaml==6.0.2",
    ],
    extras_require={
        "dev": [
            "black>=24.4.2",
            "mypy>=1.11.0",
            "types-requests",
            "types-PyYAML",
            "pytest==8.3.2",
            "pytest-asyncio==0.24.0",
            "responses==0.25.7",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries",
    ],
    # SDK supports 3.8+ but development requires 3.13+
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "damascus=damascus.cli:main",
        ],
    },
) 