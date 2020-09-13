from setuptools import setup, find_packages
import sys

if sys.version_info < (3, 6):
    sys.exit('Only Python 3.6 or greater is supported')

with open('README.md', 'r') as r:
    description = r.read()

with open('requirements.txt', 'r') as r:
    requirements = r.read()

setup(
    name='fiddy',
    version='0.0.1',
    description=description,
    author='konri',
    author_email='fiddy@gywadmin.com',
    url='https://github.com/initialgyw/fiddy',
    license='initialgyw',
    packages=find_packages(exclude=['docs', 'tests*']),
    install_requires=requirements,
)
