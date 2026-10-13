from setuptools import setup, find_packages

setup(
    name="quantumcore",
    version="0.1.0",
    description="Programmable financial core and guardrail payment router for autonomous AI agents",
    author="QuantumCore",
    packages=find_packages(where="sdk"),
    package_dir={"": "sdk"},
    install_requires=[
        "web3>=6.0.0",
        "eth-account>=0.8.0"
    ]
)
