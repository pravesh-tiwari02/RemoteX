from pathlib import Path

from setuptools import find_packages, setup  # type: ignore[import]

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='remotex_viewer',
    version='1.0.7',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'PyQt6',
        'setuptools',
    ],
    entry_points={
        'console_scripts': [
            'remotex-viewer = remotex_viewer.main:main',
        ],
    },

    description="A secure remote desktop application for Windows with the particularity of having a server entirely "
                "written in PowerShell and a cross-platform client (Python/QT6)",
    license="Apache License 2.0",
    keywords="remote desktop, remote control, remote access, remote administration, remote assistance, powershell",

    python_requires='>=3.8',
    long_description=long_description,
    long_description_content_type='text/markdown',
)
