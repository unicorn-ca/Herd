import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="unicorn-ca-herd",
    version="0.0.1",
    author="Chen Zhou",
    author_email="chen@czhou.me",
    description="A tool to automate cross-account cloudformation deployments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/unicorn-ca/Herd",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
