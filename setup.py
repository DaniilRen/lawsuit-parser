#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Setup script for Company Info Parser
"""

import os
import re
from setuptools import setup, find_packages


def get_version():
    """Get version from main module"""
    with open(os.path.join("src", "__init__.py"), "r") as f:
        content = f.read()
        version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            return version_match.group(1)
    return "0.1.0"


def get_long_description():
    """Get long description from README"""
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()


setup(
    name="company-info-parser",
    version=get_version(),
    author="Your Name",
    author_email="your.email@example.com",
    description="Parse legal company information from multiple websites using INN",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/company-info-parser",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "": ["*.json", "*.yaml", "*.yml"],
    },
    include_package_data=True,
    install_requires=[
        "psycopg2-binary>=2.9.9",
        "sqlalchemy>=2.0.23",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.2",
        "python-dotenv>=1.0.0",
        "pytest>=7.4.3",
    ],
    extras_require={
        "dev": [
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
            "isort>=5.12.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
        ],
        "scraping": [
            "selenium>=4.15.0",
            "aiohttp>=3.9.1",
            "lxml>=4.9.3",
        ],
        "monitoring": [
            "prometheus-client>=0.19.0",
            "statsd>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "company-parser=src.main:main",
            "parser-cli=src.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/company-info-parser/issues",
        "Source": "https://github.com/yourusername/company-info-parser",
        "Documentation": "https://company-info-parser.readthedocs.io/",
    },
    zip_safe=False,
)