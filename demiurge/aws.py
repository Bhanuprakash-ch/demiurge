#!/usr/bin/env python
# pylint: disable=missing-docstring,invalid-name
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

# SEE: https://coreos.com/kubernetes/docs/latest/getting-started.html

# pylint: disable=wildcard-import, unused-wildcard-import
from troposphere.constants import *
# pylint: enable=wildcard-import, unused-wildcard-import

from troposphere import (AWS_REGION, ec2, iam, Base64, FindInMap, Join, Parameter, Ref, Template,
                         autoscaling, policies, elasticloadbalancing, GetAtt, Output)

import awacs.ec2
import awacs.iam
import awacs.sts

TEMPLATE = Template()

TEMPLATE.add_version('2010-09-09')

TEMPLATE.add_mapping('RegionMap', {
    EU_CENTRAL_1:   {'AMI': 'ami-93f4ecff'},
    AP_NORTHEAST_1: {'AMI': 'ami-d56c56bb'},
    SA_EAST_1:      {'AMI': 'ami-fb129297'},
    AP_SOUTHEAST_2: {'AMI': 'ami-8bdffbe8'},
    AP_SOUTHEAST_1: {'AMI': 'ami-22529d41'},
    US_EAST_1:      {'AMI': 'ami-38c4eb52'},
    US_WEST_2:      {'AMI': 'ami-ddfc1abd'},
    US_WEST_1:      {'AMI': 'ami-cc2254ac'},
    EU_WEST_1:      {'AMI': 'ami-9f8f39ec'},
    })

VPC = TEMPLATE.add_parameter(Parameter(
    'VPC',
    Type=VPC_ID,
    ))

SUBNET = TEMPLATE.add_parameter(Parameter(
    'Subnet',
    Type=SUBNET_ID,
    ))

FLANNEL_NETWORK = TEMPLATE.add_parameter(Parameter(
    'FlannelNetwork',
    Type=STRING,
    Default='10.1.0.0/16',
    ))

FLANNEL_SUBNET_LEN = TEMPLATE.add_parameter(Parameter(
    'FlannelSubnetLen',
    Type=NUMBER,
    Default='24',
    ))

FLANNEL_SUBNET_MIN = TEMPLATE.add_parameter(Parameter(
    'FlannelSubnetMin',
    Type=STRING,
    Default='10.1.0.0',
    ))

FLANNEL_SUBNET_MAX = TEMPLATE.add_parameter(Parameter(
    'FlannelSubnetMax',
    Type=STRING,
    Default='10.1.24.0',
    ))

CLUSTER_NAME = TEMPLATE.add_parameter(Parameter(
    'ClusterName',
    Type=STRING,
    Default='kubernetes',
    ))

USERNAME = TEMPLATE.add_parameter(Parameter(
    'Username',
    Type=STRING,
    Default='admin',
    ))

PASSWORD = TEMPLATE.add_parameter(Parameter(
    'Password',
    Type=STRING,
    Default='admin',
    ))

CONSUL_DC = TEMPLATE.add_parameter(Parameter(
    'ConsulDC',
    Type=STRING,
    Default='dc1',
    ))

CONSUL_JOIN = TEMPLATE.add_parameter(Parameter(
    'ConsulJoin',
    Type=STRING,
    ))

ROLE = TEMPLATE.add_resource(iam.Role(
    'Role',
    AssumeRolePolicyDocument=awacs.aws.Policy(
        Statement=[
            awacs.aws.Statement(
                Effect=awacs.aws.Allow,
                Action=[awacs.sts.AssumeRole],
                Principal=awacs.aws.Principal('Service', ['ec2.amazonaws.com']),
                ),
            ],
        ),
    ))

POLICY = TEMPLATE.add_resource(iam.PolicyType(
    'Policy',
    PolicyName='coreos',
    PolicyDocument=awacs.aws.Policy(
        Statement=[
            awacs.aws.Statement(
                Effect=awacs.aws.Allow,
                Action=[awacs.ec2.EC2Action('Describe*')],
                Resource=['*'],
                ),
            awacs.aws.Statement(
                Effect=awacs.aws.Allow,
                Action=[awacs.aws.Action('autoscaling', 'Describe*')],
                Resource=['*'],
                ),
            ],
        ),
    Roles=[Ref(ROLE)],
    ))

INSTANCE_PROFILE = TEMPLATE.add_resource(iam.InstanceProfile(
    'InstanceProfile',
    Roles=[Ref(ROLE)],
    ))

INSTANCE_TYPE = TEMPLATE.add_parameter(Parameter(
    'InstanceType',
    Type=STRING,
    Default=M4_LARGE,
    AllowedValues=[M4_LARGE, M4_XLARGE, M4_2XLARGE, M4_4XLARGE, M4_10XLARGE],
    ))

KEY_NAME = TEMPLATE.add_parameter(Parameter(
    'KeyName',
    Type=KEY_PAIR_NAME,
    ))

SECURITY_GROUP = TEMPLATE.add_resource(ec2.SecurityGroup(
    'SecurityGroup',
    GroupDescription='Kubernetes Security Group',
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol='tcp',
            FromPort='22',
            ToPort='22',
            CidrIp='0.0.0.0/0',
            ),
        ec2.SecurityGroupRule(
            IpProtocol='tcp',
            FromPort='30000',
            ToPort='32767',
            CidrIp='0.0.0.0/0',
            ),
        ],
    SecurityGroupEgress=[
        ec2.SecurityGroupRule(
            IpProtocol='-1',
            FromPort='-1',
            ToPort='-1',
            CidrIp='0.0.0.0/0',
            ),
        ],
    VpcId=Ref(VPC),
    ))

TEMPLATE.add_resource(ec2.SecurityGroupIngress(
    'etcdClientCommunicationSecurityGroupIngress',
    IpProtocol='tcp',
    FromPort='2379',
    ToPort='2379',
    SourceSecurityGroupId=Ref(SECURITY_GROUP),
    GroupId=Ref(SECURITY_GROUP),
    ))

TEMPLATE.add_resource(ec2.SecurityGroupIngress(
    'etcdServerToServerCommunicationSecurityGroupIngress',
    IpProtocol='tcp',
    FromPort='2380',
    ToPort='2380',
    SourceSecurityGroupId=Ref(SECURITY_GROUP),
    GroupId=Ref(SECURITY_GROUP),
    ))

TEMPLATE.add_resource(ec2.SecurityGroupIngress(
    'flannelVXLANSecurityGroupIngress',
    IpProtocol='udp',
    FromPort='8472',
    ToPort='8472',
    SourceSecurityGroupId=Ref(SECURITY_GROUP),
    GroupId=Ref(SECURITY_GROUP),
    ))

API_SERVER_SECURITY_GROUP = TEMPLATE.add_resource(ec2.SecurityGroup(
    'ServerSecurityGroup',
    GroupDescription='Kubernetes API Server Security Group',
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol='tcp',
            FromPort='6443',
            ToPort='6443',
            CidrIp='0.0.0.0/0',
            ),
        ],
    VpcId=Ref(VPC),
    ))

API_SERVER_LOAD_BALANCER = TEMPLATE.add_resource(elasticloadbalancing.LoadBalancer(
    'APIServerLoadBalancer',
    HealthCheck=elasticloadbalancing.HealthCheck(
        Target='TCP:6443',
        HealthyThreshold='3',
        UnhealthyThreshold='5',
        Interval='30',
        Timeout='5',
        ),
    Listeners=[
        elasticloadbalancing.Listener(
            LoadBalancerPort='8080',
            InstancePort='8080',
            Protocol='HTTP',
            ),
        elasticloadbalancing.Listener(
            LoadBalancerPort='6443',
            InstancePort='6443',
            Protocol='TCP',
            ),
        ],
    Scheme='internal',
    SecurityGroups=[Ref(API_SERVER_SECURITY_GROUP)],
    Subnets=[Ref(SUBNET)],
    ))

LAUNCH_CONFIGURATION = TEMPLATE.add_resource(autoscaling.LaunchConfiguration(
    'LaunchConfiguration',
    IamInstanceProfile=Ref(INSTANCE_PROFILE),
    ImageId=FindInMap('RegionMap', Ref(AWS_REGION), 'AMI'),
    InstanceType=Ref(INSTANCE_TYPE),
    KeyName=Ref(KEY_NAME),
    SecurityGroups=[Ref(SECURITY_GROUP), Ref(API_SERVER_SECURITY_GROUP)],
    UserData=Base64(Join('', [
        '#cloud-config\n\n',
        'coreos:\n',
        '  etcd2:\n',
        '    advertise-client-urls: http://$private_ipv4:2379\n',
        '    initial-advertise-peer-urls: http://$private_ipv4:2380\n',
        '    listen-client-urls: http://0.0.0.0:2379\n',
        '    listen-peer-urls: http://$private_ipv4:2380\n',
        '  units:\n',
        '    - name: etcd-peers.service\n',
        '      command: start\n',
        '      content: |\n',
        '        [Unit]\n',
        '        Description=Write a file with the etcd peers that we should bootstrap to\n',
        '        After=docker.service\n'
        '        Requires=docker.service\n\n',
        '        [Service]\n',
        '        Type=oneshot\n',
        '        RemainAfterExit=yes\n',
        '        ExecStart=/usr/bin/docker pull monsantoco/etcd-aws-cluster:latest\n',
        '        ExecStart=/usr/bin/docker run --rm=true -v /etc/sysconfig/:/etc/sysconfig/ ',
        'monsantoco/etcd-aws-cluster:latest\n',
        '    - name: etcd2.service\n'
        '      command: start\n',
        '      drop-ins:\n'
        '        - name: 30-etcd_peers.conf\n',
        '          content: |\n',
        '            [Unit]\n',
        '            After=etcd-peers.service\n'
        '            Requires=etcd-peers.service\n\n',
        '            [Service]\n',
        '            # Load the other hosts in the etcd leader autoscaling group from file\n',
        '            EnvironmentFile=/etc/sysconfig/etcd-peers\n',
        '    - name: fleet.service\n',
        '      command: start\n',
        '    - name: flanneld.service\n',
        '      drop-ins:\n',
        '        - name: 50-network-config.conf\n',
        '          content: |\n',
        '            [Service]\n',
        '            ExecStartPre=/usr/bin/etcdctl set /coreos.com/network/config \'{ "Network": "',
        Ref(FLANNEL_NETWORK), '", "SubnetLen": ', Ref(FLANNEL_SUBNET_LEN), ', "SubnetMin": "',
        Ref(FLANNEL_SUBNET_MIN), '", "SubnetMax": "', Ref(FLANNEL_SUBNET_MAX), '" }\'\n',
        '      command: start\n',
        '    - name: kubelet.service\n',
        '      command: start\n',
        '      drop-ins:\n',
        '        - name: local.conf\n',
        '          content: |\n',
        '            [Service]\n',
        '            ExecStart=\n',
        '            ExecStart=/usr/bin/kubelet \\\n',
        '              --api-servers=http://127.0.0.1:8080 \\\n',
        '              --register-node=true \\\n',
        '              --allow-privileged=true \\\n',
        '              --config=/etc/kubernetes/manifests\n',
        '    - name: kube-system.service\n',
        '      command: start\n',
        '      content: |\n',
        '        [Unit]\n',
        '        After=kubelet.service\n',
        '        Requires=kubelet.service\n\n',
        '        [Service]\n',
        '        Type=oneshot\n',
        '        ExecStart=/bin/sh -c \'while true; do curl -XPOST ',
        '-d\\\'{"apiVersion":"v1","kind":"Namespace","metadata":{"name":"kube-system"}}\\\' -sS ',
        '"http://127.0.0.1:8080/api/v1/namespaces" && break || sleep 20; done\'\n',
        'write_files:\n',
        '  - path: /etc/kubernetes/manifests/kube-apiserver.yaml\n',
        '    content: |\n',
        '      apiVersion: v1\n',
        '      kind: Pod\n',
        '      metadata:\n',
        '        name: kube-apiserver\n',
        '        namespace: kube-system\n',
        '      spec:\n',
        '        hostNetwork: true\n',
        '        containers:\n',
        '        - name: kube-apiserver\n',
        '          image: gcr.io/google_containers/hyperkube:v1.1.2\n',
        '          command:\n',
        '          - /hyperkube\n',
        '          - apiserver\n',
        '          - --etcd-servers=http://127.0.0.1:2379\n',
        '          - --allow-privileged=true\n',
        '          - --service-cluster-ip-range=10.3.0.0/24\n',
        '          - --admission-control=NamespaceLifecycle,LimitRanger,SecurityContextDeny,',
        'ResourceQuota\n',
        '          - --runtime-config=extensions/v1beta1/deployments=true,',
        'extensions/v1beta1/daemonsets=true\n',
        '          - --cloud-provider=aws\n',
        '          - --external-hostname=', GetAtt(API_SERVER_LOAD_BALANCER, 'DNSName'), '\n',
        '          - --basic-auth-file=/srv/kubernetes/basic_auth.csv\n',
        '          ports:\n',
        '          - containerPort: 443\n',
        '            hostPort: 443\n',
        '            name: https\n',
        '          - containerPort: 8080\n',
        '            hostPort: 8080\n',
        '            name: local\n',
        '          volumeMounts:\n',
        '          - mountPath: /etc/ssl/certs\n',
        '            name: ssl-certs-host\n',
        '            readOnly: true\n',
        '          - mountPath: /srv/kubernetes/basic_auth.csv\n',
        '            name: basic-auth-file\n',
        '            readOnly: true\n',
        '        volumes:\n',
        '        - hostPath:\n',
        '            path: /usr/share/ca-certificates\n',
        '          name: ssl-certs-host\n',
        '        - hostPath:\n',
        '            path: /srv/kubernetes/basic_auth.csv\n',
        '          name: basic-auth-file\n',
        '  - path: /etc/kubernetes/manifests/kube-proxy.yaml\n',
        '    content: |\n',
        '      apiVersion: v1\n',
        '      kind: Pod\n',
        '      metadata:\n',
        '        name: kube-proxy\n',
        '        namespace: kube-system\n',
        '      spec:\n',
        '        hostNetwork: true\n',
        '        containers:\n',
        '        - name: kube-proxy\n',
        '          image: gcr.io/google_containers/hyperkube:v1.1.2\n',
        '          command:\n',
        '          - /hyperkube\n',
        '          - proxy\n',
        '          - --master=http://127.0.0.1:8080\n',
        '          - --proxy-mode=iptables\n',
        '          securityContext:\n',
        '            privileged: true\n',
        '          volumeMounts:\n',
        '          - mountPath: /etc/ssl/certs\n',
        '            name: ssl-certs-host\n',
        '            readOnly: true\n',
        '        volumes:\n',
        '        - hostPath:\n',
        '            path: /usr/share/ca-certificates\n',
        '          name: ssl-certs-host\n',
        '  - path: /etc/kubernetes/manifests/kube-podmaster.yaml\n',
        '    content: |\n',
        '      apiVersion: v1\n',
        '      kind: Pod\n',
        '      metadata:\n',
        '        name: kube-podmaster\n',
        '        namespace: kube-system\n',
        '      spec:\n',
        '        hostNetwork: true\n',
        '        containers:\n',
        '        - name: scheduler-elector\n',
        '          image: gcr.io/google_containers/podmaster:1.1\n',
        '          command:\n',
        '          - /podmaster\n',
        '          - --etcd-servers=http://127.0.0.1:2379\n',
        '          - --key=scheduler\n',
        '          - --whoami=$private_ipv4\n',
        '          - --source-file=/src/manifests/kube-scheduler.yaml\n',
        '          - --dest-file=/dst/manifests/kube-scheduler.yaml\n',
        '          volumeMounts:\n',
        '          - mountPath: /src/manifests\n',
        '            name: manifest-src\n',
        '            readOnly: true\n',
        '          - mountPath: /dst/manifests\n',
        '            name: manifest-dst\n',
        '        - name: controller-manager-elector\n',
        '          image: gcr.io/google_containers/podmaster:1.1\n',
        '          command:\n',
        '          - /podmaster\n',
        '          - --etcd-servers=http://127.0.0.1:2379\n',
        '          - --key=controller\n',
        '          - --whoami=$private_ipv4\n',
        '          - --source-file=/src/manifests/kube-controller-manager.yaml\n',
        '          - --dest-file=/dst/manifests/kube-controller-manager.yaml\n',
        '          terminationMessagePath: /dev/termination-log\n',
        '          volumeMounts:\n',
        '          - mountPath: /src/manifests\n',
        '            name: manifest-src\n',
        '            readOnly: true\n',
        '          - mountPath: /dst/manifests\n',
        '            name: manifest-dst\n',
        '        volumes:\n',
        '        - hostPath:\n',
        '            path: /srv/kubernetes/manifests\n',
        '          name: manifest-src\n',
        '        - hostPath:\n',
        '            path: /etc/kubernetes/manifests\n',
        '          name: manifest-dst\n',
        '  - path: /srv/kubernetes/manifests/kube-controller-manager.yaml\n',
        '    content: |\n',
        '      apiVersion: v1\n',
        '      kind: Pod\n',
        '      metadata:\n',
        '        name: kube-controller-manager\n',
        '        namespace: kube-system\n',
        '      spec:\n',
        '        hostNetwork: true\n',
        '        containers:\n',
        '        - name: kube-controller-manager\n',
        '          image: gcr.io/google_containers/hyperkube:v1.1.2\n',
        '          command:\n',
        '          - /hyperkube\n',
        '          - controller-manager\n',
        '          - --master=http://127.0.0.1:8080\n',
        '          - --cloud-provider=aws\n',
        '          livenessProbe:\n',
        '            httpGet:\n',
        '              host: 127.0.0.1\n',
        '              path: /healthz\n',
        '              port: 10252\n',
        '            initialDelaySeconds: 15\n',
        '            timeoutSeconds: 1\n',
        '          volumeMounts:\n',
        '          - mountPath: /etc/ssl/certs\n',
        '            name: ssl-certs-host\n',
        '            readOnly: true\n',
        '        volumes:\n',
        '        - hostPath:\n',
        '            path: /usr/share/ca-certificates\n',
        '          name: ssl-certs-host\n',
        '  - path: /srv/kubernetes/manifests/kube-scheduler.yaml\n',
        '    content: |\n',
        '      apiVersion: v1\n',
        '      kind: Pod\n',
        '      metadata:\n',
        '        name: kube-scheduler\n',
        '        namespace: kube-system\n',
        '      spec:\n',
        '        hostNetwork: true\n',
        '        containers:\n',
        '        - name: kube-scheduler\n',
        '          image: gcr.io/google_containers/hyperkube:v1.1.2\n',
        '          command:\n',
        '          - /hyperkube\n',
        '          - scheduler\n',
        '          - --master=http://127.0.0.1:8080\n',
        '          livenessProbe:\n',
        '            httpGet:\n',
        '              host: 127.0.0.1\n',
        '              path: /healthz\n',
        '              port: 10251\n',
        '            initialDelaySeconds: 15\n',
        '            timeoutSeconds: 1\n',
        '  - path: /srv/kubernetes/manifests/kube-system.yaml\n',
        '    content: |\n',
        '      apiVersion: v1\n',
        '      kind: Namespace\n',
        '      metadata:\n',
        '        name: kube-system\n',
        '  - path: /srv/kubernetes/basic_auth.csv\n',
        '    content: |\n',
        '      ', Ref(PASSWORD), ',', Ref(USERNAME), ',admin\n',
        '  - path: /etc/kubernetes/manifests/kube2consul.yaml\n',
        '    content: |\n',
        '      apiVersion: v1\n',
        '      kind: Pod\n',
        '      metadata:\n',
        '        name: kube2consul\n',
        '        namespace: kube-system\n',
        '      spec:\n',
        '        hostNetwork: true\n',
        '        containers:\n',
        '        - name: consul-agent\n',
        '          image: gliderlabs/consul-agent:0.6\n',
        '          args:\n',
        '          - -advertise=$private_ipv4\n',
        '          - -dc=', Ref(CONSUL_DC), '\n',
        '          - -join=', Ref(CONSUL_JOIN), '\n',
        '          ports:\n',
        '          - hostPort: 8301\n',
        '            containerPort: 8301\n',
        '            protocol: TCP\n',
        '            hostIP: 10.10.6.77\n',
        '          - hostPort: 8301\n',
        '            containerPort: 8301\n',
        '            protocol: UDP\n',
        '            hostIP: 10.10.6.77\n',
        '        - name: kube2consul\n',
        '          image: jmccarty3/kube2consul:latest\n',
        '          command:\n',
        '          - /kube2consul\n',
        '          - -consul-agent=http://127.0.0.1:8500\n',
        '          - -kube_master_url=http://127.0.0.1:8080\n',
        ])),
    ))

AUTO_SCALING_GROUP = TEMPLATE.add_resource(autoscaling.AutoScalingGroup(
    'AutoScalingGroup',
    DesiredCapacity='1',
    Tags=[autoscaling.Tag('Name', 'Kubernetes Master', True)],
    LaunchConfigurationName=Ref(LAUNCH_CONFIGURATION),
    LoadBalancerNames=[Ref(API_SERVER_LOAD_BALANCER)],
    MinSize='1',
    MaxSize='3',
    VPCZoneIdentifier=[Ref(SUBNET)],
    UpdatePolicy=policies.UpdatePolicy(
        AutoScalingRollingUpdate=policies.AutoScalingRollingUpdate(
            MinInstancesInService='1',
            MaxBatchSize='1',
            ),
        ),
    ))

TEMPLATE.add_output(Output(
    'APIServer',
    Value=Join('', ['https://', GetAtt(API_SERVER_LOAD_BALANCER, 'DNSName'), ':6443']),
    ))

if __name__ == '__main__':
    print TEMPLATE.to_json()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100