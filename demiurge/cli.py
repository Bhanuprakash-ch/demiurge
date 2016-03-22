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

import logging

import click
import connexion
from connexion.resolver import RestyResolver
from flask_httpauth import HTTPBasicAuth

from . import __version__

AUTH = HTTPBasicAuth()

USERS = {}

@AUTH.get_password
def get_pw(username):
    if username in USERS:
        return USERS.get(username)
    else:
        return None

BOTO3_CLIENT_KWARGS = {}
STACK_PARAMETERS = []

@click.command()
@click.option('--username', envvar='USERNAME', required=True)
@click.option('--password', envvar='PASSWORD', required=True)
@click.option('--region-name', envvar='AWS_DEFAULT_REGION', default='us-west-2')
@click.option('--aws-access-key-id', envvar='AWS_ACCESS_KEY_ID')
@click.option('--aws-secret-access-key', envvar='AWS_SECRET_ACCESS_KEY')
@click.option('--vpc', envvar='VPC', required=True)
@click.option('--subnet', envvar='SUBNET', required=True)
@click.option('--key-name', envvar='KEY_NAME', required=True)
@click.option('--debug/--no-debug', '-d', default=False)
@click.option('--port', '-p', envvar='PORT', default=8080)
def cli(username, password, port, debug, **kwargs):
    USERS[username] = password

    for keyword in ['region_name', 'aws_access_key_id', 'aws_secret_access_key']:
        BOTO3_CLIENT_KWARGS[keyword] = kwargs[keyword]

    STACK_PARAMETERS.append({'ParameterKey': 'VPC', 'ParameterValue': kwargs['vpc']})
    STACK_PARAMETERS.append({'ParameterKey': 'Subnet', 'ParameterValue': kwargs['subnet']})
    STACK_PARAMETERS.append({'ParameterKey': 'KeyName', 'ParameterValue': kwargs['key_name']})

    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)

    app = connexion.App(__name__, specification_dir='swagger/', arguments={'version': __version__},
                        debug=debug)
    app.add_api('clusters.yaml', resolver=RestyResolver('kube_tap.api'))
    app.run(port=port)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100
