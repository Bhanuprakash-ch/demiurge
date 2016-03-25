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

from . import __version__, APP, APPLICATION, main

@click.command()
@click.option('--debug/--no-debug', '-d', default=False)
@click.option('--port', '-p', envvar='PORT', default=8080)

@click.option('--username', envvar='USERNAME', required=True,
              help='Username for basic authentication.')
@click.option('--password', envvar='PASSWORD', required=True,
              help='Password for basic authentication.')

@click.option('--region-name', envvar='AWS_DEFAULT_REGION', default='us-west-2',
              help='The region to use.')
@click.option('--aws-access-key-id', envvar='AWS_ACCESS_KEY_ID',
              help='The AWS Access Key ID.')
@click.option('--aws-secret-access-key', envvar='AWS_SECRET_ACCESS_KEY',
              help='The AWS Secret Access Key.')

@click.option('--os-username', envvar='OS_USERNAME', help='Your OpenStack username.')
@click.option('--os-password', envvar='OS_PASSWORD', help='Your OpenStack password.')
@click.option('--os-tenant-id', envvar='OS_TENANT_ID', help='Your OpenStack tenant.')
@click.option('--os-auth-url', envvar='OS_AUTH_URL', help='Your OpenStack auth endpoint.')

@click.option('--vpc', envvar='VPC', required=True,
              help='VPC ID of your exsiting Virtual Private Cloud (VPC) where you want to deploy '
                   'Kubernetes clusters.')
@click.option('--subnet', envvar='SUBNET', required=True,
              help='Subnet ID of the existing subnet in your VPC where you want to deploy '
                   'Kubernetes nodes.')
@click.option('--key-name', envvar='KEY_NAME', required=True,
              help='Name of an existing EC2 Key Pair. Kubernetes instances will launch with '
                   'this Key Pair.')
@click.option('--consul-dc', envvar='CONSUL_DC', required=True,
              help='The datacenter in which the Consul agent is running.')
@click.option('--consul-join', envvar='CONSUL_JOIN', required=True,
              help='Address of another Consul agent to join.')
def cli(debug, port, username, password, **kwargs):
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)

    APP.debug = debug
    APP.port = port

    APPLICATION.config['USERS'][username] = password

    APPLICATION.config['AWS_DEFAULT_REGION_NAME'] = kwargs['region_name']
    APPLICATION.config['AWS_ACCESS_KEY_ID'] = kwargs['aws_access_key_id']
    APPLICATION.config['AWS_SECRET_ACCESS_KEY'] = kwargs['aws_secret_access_key']

    APPLICATION.config['VPC'] = kwargs['vpc']
    APPLICATION.config['SUBNET'] = kwargs['subnet']
    APPLICATION.config['KEY_NAME'] = kwargs['key_name']
    APPLICATION.config['CONSUL_DC'] = kwargs['consul_dc']
    APPLICATION.config['CONSUL_JOIN'] = kwargs['consul_join']

    main()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100
