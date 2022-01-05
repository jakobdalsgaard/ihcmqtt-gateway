import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="ihcmqtt-gateway",
    version="1.0.1",
    description="IHC-MQTT gateway",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/jakobdalsgaard/ihcmqtt",
    author="Jakob Dalsgaard",
    author_email="jakob@dalsgaard.net",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["ihcmqtt"],
    include_package_data=False,
    install_requires=["paho-mqtt", "ihcsdk"],
    entry_points={
        "console_scripts": [
            "ihcqmtt-gateway=ihcmqtt.gateway:main",
        ]
    },
)
