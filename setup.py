from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of the README file for the long description
here = Path(__file__).parent
long_description = (here / "README.md").read_text()

setup(
    name="precise_money",
    version="0.1.4",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "pydantic-core>=2.23.0",
    ],
    extras_require={
        "dev": ["pytest", "twine", "pydantic"],
    },
    author="Cathleen Turner",
    author_email="cathleen.turner@autaly.co",
    description="A Python library for handling monetary values and currencies with maniacal attention to precision. PreciseMoney offers robust tools for financial calculations and currency management, ensuring accuracy in even the most complex monetary operations. Perfect for developers who lose sleep over floating-point errors.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ListfulAl/PreciseMoney",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",  # Add specific Python versions
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
