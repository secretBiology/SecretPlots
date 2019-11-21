import setuptools

with open("PYPI.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="SecretPlots",
    version="0.1.1",
    author="Rohit Suratekar",
    author_email="rohitsuratekar@gmail.com",
    description="Make plotting great again!",
    long_description_content_type="text/markdown",
    long_description=long_description,
    url="https://github.com/secretBiology/SecretPlots",
    packages=setuptools.find_packages(),
    license='MIT License',
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 1 - Planning",
        "Natural Language :: English",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics"
    ],
)
