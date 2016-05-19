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

import connexion
from connexion.resolver import RestyResolver
from flask_httpauth import HTTPBasicAuth

__version__ = '0.2.7'

APP = connexion.App(__name__, specification_dir='swagger/', arguments={'version': __version__})
APPLICATION = APP.app
AUTH = HTTPBasicAuth()

APPLICATION.config['USERS'] = {}

@AUTH.get_password
def get_password(username):
    return APPLICATION.config['USERS'].get(username)

def main():
    APP.add_api('clusters.yaml', resolver=RestyResolver(__name__ + '.api'))
    APP.run()

if __name__ == '__main__':
    main()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100
