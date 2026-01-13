"""
Setup script for Security Authentication System
"""

from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

with open("README.md") as f:
    readme = f.read()

setup(
    name="security-auth-system",
    version="1.0.0",
    author="Security Team",
    author_email="security@example.com",
    description="Comprehensive security authentication system with JWT, RBAC, rate limiting, and more",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/security-auth-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Security",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "postgresql": ["psycopg2-binary>=2.9.7"],
        "mysql": ["pymysql>=1.1.0"],
        "monitoring": ["prometheus-client>=0.17.0"],
        "documentation": ["flasgger>=0.9.7"],
    },
    keywords="security authentication jwt rbac rate-limiting audit encryption",
    project_urls={
        "Bug Reports": "https://github.com/your-org/security-auth-system/issues",
        "Source": "https://github.com/your-org/security-auth-system",
        "Documentation": "https://security-auth-system.readthedocs.io/",
    },
)
