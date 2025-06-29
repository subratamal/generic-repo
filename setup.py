import os

from setuptools import find_packages, setup

# Conditional package directory mapping for local testing
package_dir = {}
if os.getenv('LOCAL_TESTING', '').lower() in ('1', 'true', 'yes'):
    package_dir = {'generic_repo': 'src'}

setup(
    package_dir=package_dir,
    packages=['generic_repo'] if package_dir else find_packages(where='src'),
)
