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

import re
from time import sleep

import boto3
from botocore.exceptions import ClientError
import fauxfactory
from connexion import NoContent
import logging

from .. import APP, APPLICATION, AUTH
from ..aws import TEMPLATE

logger = logging.getLogger('clusters.api')

CLIENT = boto3.client(
    'cloudformation',
    region_name=APPLICATION.config.get('AWS_DEFAULT_REGION_NAME'),
    aws_access_key_id=APPLICATION.config.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=APPLICATION.config.get('AWS_SECRET_ACCESS_KEY'),
    )

STACK_NAME = 'TAP-Kubernetes-{}'
MAX_RETRIES = 10

def __cluster(stack):
    cluster = {}

    if 'Parameters' not in stack:
        return None

    for parameter in stack['Parameters']:
        if parameter['ParameterKey'] == 'ClusterName':
            cluster['cluster_name'] = parameter['ParameterValue']
        elif parameter['ParameterKey'] == 'Username':
            cluster['username'] = parameter['ParameterValue']
        elif parameter['ParameterKey'] == 'Password':
            cluster['password'] = parameter['ParameterValue']
        elif (parameter['ParameterKey'] == 'VPC' and
              parameter['ParameterValue'] != APPLICATION.config['VPC']):
            return None

    for output in stack['Outputs']:
        if output['OutputKey'] == 'APIServer':
            cluster['api_server'] = output['OutputValue']
        if output['OutputKey'] == 'ConsulHTTPAPI':
            cluster['consul_http_api'] = output['OutputValue']

    return cluster

@AUTH.login_required
def search():
    clusters = []

    response = CLIENT.describe_stacks()

    for stack in response['Stacks']:
        if re.match(r'(CREATE|UPDATE)_COMPLETE', stack['StackStatus']):
            cluster = __cluster(stack)

            if cluster:
                clusters.append(cluster)

    return clusters, 200

@AUTH.login_required
def get(cluster_name):
    response = CLIENT.describe_stacks()

    for stack in response['Stacks']:
        if stack['StackName'] == STACK_NAME.format(cluster_name):
            if re.match(r'(CREATE|UPDATE)_COMPLETE', stack['StackStatus']):
                return __cluster(stack), 200
            elif re.match(r'(CREATE|UPDATE)_IN_PROGRESS', stack['StackStatus']):
                return NoContent, 204
            elif re.match(r'DELETE_(IN_PROGRESS|COMPLETE)', stack['StackStatus']):
                return NoContent, 404
            else:
                error_msg = stack['StackName'] + ': ' + stack['StackStatus']
                if 'StackStatusReason' in stack:
                    error_msg += ': ' + stack['StackStatusReason']
                logger.error(error_msg)
                return NoContent, 404

    return NoContent, 404

@AUTH.login_required
def put(cluster_name):
    try:
        CLIENT.create_stack(
            StackName=STACK_NAME.format(cluster_name),
            TemplateBody=TEMPLATE.to_json(),
            Parameters=[
                {
                    'ParameterKey': 'VPC',
                    'ParameterValue': APPLICATION.config['VPC'],
                },
                {
                    'ParameterKey': 'Subnet',
                    'ParameterValue': APPLICATION.config['SUBNET']},
                {
                    'ParameterKey': 'KeyName',
                    'ParameterValue': APPLICATION.config['KEY_NAME'],
                },
                {
                    'ParameterKey': 'ClusterName',
                    'ParameterValue': cluster_name,
                },
                {
                    'ParameterKey': 'Password',
                    'ParameterValue': fauxfactory.gen_string('alphanumeric', 16),
                },
                {
                    'ParameterKey': 'ConsulDC',
                    'ParameterValue': APPLICATION.config['CONSUL_DC'],
                },
                {
                    'ParameterKey': 'ConsulJoin',
                    'ParameterValue': APPLICATION.config['CONSUL_JOIN'],
                },
                ],
            DisableRollback=APP.debug,
            Capabilities=[
                'CAPABILITY_IAM',
                ],
            )
    except ClientError as exception:
        if exception.response['Error']['Code'] == 'AlreadyExistsException':
            return NoContent, 409
        else:
            raise

    in_progress = False
    retries = 0

    while not in_progress and retries < MAX_RETRIES:
        response = CLIENT.describe_stacks(StackName=STACK_NAME.format(cluster_name))

        for stack in response['Stacks']:
            in_progress = bool(re.match(r'(CREATE|UPDATE)_IN_PROGRESS', stack['StackStatus']))

        # SEE: http://docs.aws.amazon.com/general/latest/gr/api-retries.html
        secs = 2**retries*0.1
        sleep(secs)
        retries += 1

    return NoContent, 202 if in_progress else 500

@AUTH.login_required
def delete(cluster_name):
    CLIENT.delete_stack(
        StackName=STACK_NAME.format(cluster_name),
        )

    return NoContent, 204

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100
