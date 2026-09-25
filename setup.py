from setuptools import setup, find_packages

setup(
    name='qcore-enterprise',
    version='1.0.0',
    py_modules=['qcore'],
    install_requires=[
        'numpy',
        'matplotlib'
    ],
    entry_points={
        'console_scripts': [
            'qcore=qcore:main',
        ],
    },
    author='Christina Holt',
    description='Enterprise Quantum Risk CBOM Scanner & Hardware Transpilation Engine',
)
