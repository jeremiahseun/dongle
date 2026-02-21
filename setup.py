from setuptools import setup, find_packages

setup(
    name="dongle",
    version="0.1.0",
    description="Fast, fuzzy directory navigation for any terminal",
    author="Dongle Contributors",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[
        "prompt_toolkit>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "dongle=dongle.init_cmd:main",
            "dongle-pick=dongle.main:cmd_pick",
            "dongle-scan=dongle.main:cmd_scan",
            "dongle-list=dongle.main:cmd_list",
        ],
    },
)
