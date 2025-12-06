from setuptools import setup, find_packages

setup(
    name="entra-saml-provisioner",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "azure-identity",
        "requests",
        "PyYAML",
        "pydantic"
    ],
    entry_points={
        "console_scripts": [
            "entra-provision=entra_provisioner.main:main",
        ],
    },
)
