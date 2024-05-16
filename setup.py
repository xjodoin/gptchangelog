from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="gptchangelog",
    version="0.5.0",
    author="Xavier Jodoin",
    author_email="xavier@jodoin.me",
    description="Automatically generate a changelog using AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/xjodoin/gptchangelog",
    packages=find_packages(),
    package_data={"gptchangelog": ["templates/*.txt"]},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.6",
    install_requires=[
        "openai",
        "gitpython",
        "configparser",
    ],
    entry_points={
        "console_scripts": [
            "gptchangelog=gptchangelog:main",
        ],
    },
)
