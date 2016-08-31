# pylint: disable=missing-docstring
# Copyright (c) 2016 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from setuptools import setup, find_packages

setup(
    name='demiurge',
    version='0.8.3',
    packages=find_packages(),
    install_requires=[
            'awacs==0.5.4',
            'boto3==1.3.1',
            'click==6.6',
            'connexion==1.0.103',
            'fauxfactory==2.0.9',
            'Flask-HTTPAuth',
            'troposphere==1.6.0',
            'pyopenssl',
            'cffi==1.7.0'
            ],
    author='Maciej Strzelecki',
    author_email='maciej.strzelecki@intel.com',
    license='Apache License, Version 2.0',
    entry_points={
        'console_scripts': [
            'demiurge = demiurge.cli:cli',
            ],
        },
)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100
