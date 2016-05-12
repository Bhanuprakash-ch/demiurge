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

# CoreOS 991.2.0
# SEE: https://coreos.com/os/docs/latest/booting-on-ec2.html#beta
TEMPLATE.add_mapping('RegionMap', {
    EU_CENTRAL_1:   {'AMI': 'ami-e83ddb87'},
    AP_NORTHEAST_1: {'AMI': 'ami-67e9fd09'},
    SA_EAST_1:      {'AMI': 'ami-9666eafa'},
    AP_SOUTHEAST_2: {'AMI': 'ami-9a7d5ef9'},
    AP_SOUTHEAST_1: {'AMI': 'ami-b8d319db'},
    US_EAST_1:      {'AMI': 'ami-cfaba5a5'},
    US_WEST_2:      {'AMI': 'ami-141df674'},
    US_WEST_1:      {'AMI': 'ami-6c037e0c'},
    EU_WEST_1:      {'AMI': 'ami-d149cea2'},
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

DOCKER_GRAPH_SIZE = TEMPLATE.add_parameter(Parameter(
    'DockerGraphSize',
    Type=NUMBER,
    Default='120',
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
                Action=[
                    awacs.ec2.EC2Action('Describe*'),
                    awacs.ec2.EC2Action('CreateTags'),
                    awacs.ec2.EC2Action('AttachVolume'),
                    awacs.ec2.EC2Action('CreateVolume'),
                    awacs.ec2.EC2Action('DeleteVolume'),
                    awacs.ec2.EC2Action('DetachVolume'),
                    awacs.ec2.EC2Action('SecurityGroup'),
                ],
                Resource=['*'],
                ),
            awacs.aws.Statement(
                Effect=awacs.aws.Allow,
                Action=[
                    awacs.aws.Action('autoscaling', 'Describe*'),
                    awacs.aws.Action('elasticloadbalancing', 'Describe*'),
                ],
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
            FromPort='8301',
            ToPort='8301',
            CidrIp='0.0.0.0/0',
            ),
        ec2.SecurityGroupRule(
            IpProtocol='udp',
            FromPort='8301',
            ToPort='8301',
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
            FromPort='443',
            ToPort='443',
            CidrIp='0.0.0.0/0',
            ),
        ],
    VpcId=Ref(VPC),
    ))

API_SERVER_LOAD_BALANCER = TEMPLATE.add_resource(elasticloadbalancing.LoadBalancer(
    'APIServerLoadBalancer',
    HealthCheck=elasticloadbalancing.HealthCheck(
        Target='TCP:443',
        HealthyThreshold='3',
        UnhealthyThreshold='5',
        Interval='30',
        Timeout='5',
        ),
    Listeners=[
        elasticloadbalancing.Listener(
            LoadBalancerPort='443',
            InstancePort='443',
            Protocol='TCP',
            ),
        ],
    Scheme='internal',
    SecurityGroups=[Ref(API_SERVER_SECURITY_GROUP)],
    Subnets=[Ref(SUBNET)],
    ))

CONSUL_HTTP_API_SECURITY_GROUP = TEMPLATE.add_resource(ec2.SecurityGroup(
    'ConsulHTTPAPISecurityGroup',
    GroupDescription='Consul HTTP API Security Group',
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol='tcp',
            FromPort='8500',
            ToPort='8500',
            CidrIp='0.0.0.0/0',
            ),
        ],
    VpcId=Ref(VPC),
    ))

CONSUL_HTTP_API_LOAD_BALANCER = TEMPLATE.add_resource(elasticloadbalancing.LoadBalancer(
    'ConsulHTTPAPILoadBalancer',
    HealthCheck=elasticloadbalancing.HealthCheck(
        Target='TCP:8500',
        HealthyThreshold='3',
        UnhealthyThreshold='5',
        Interval='30',
        Timeout='5',
        ),
    Listeners=[
        elasticloadbalancing.Listener(
            LoadBalancerPort='8500',
            InstancePort='8500',
            Protocol='HTTP',
            ),
        ],
    Scheme='internal',
    SecurityGroups=[Ref(CONSUL_HTTP_API_SECURITY_GROUP)],
    Subnets=[Ref(SUBNET)],
    ))

LAUNCH_CONFIGURATION = TEMPLATE.add_resource(autoscaling.LaunchConfiguration(
    'LaunchConfiguration',
    BlockDeviceMappings=[
        ec2.BlockDeviceMapping(
            DeviceName='/dev/sdb',
            Ebs=ec2.EBSBlockDevice(
                VolumeSize=Ref(DOCKER_GRAPH_SIZE),
                )
            ),
        ],
    IamInstanceProfile=Ref(INSTANCE_PROFILE),
    ImageId=FindInMap('RegionMap', Ref(AWS_REGION), 'AMI'),
    InstanceType=Ref(INSTANCE_TYPE),
    KeyName=Ref(KEY_NAME),
    SecurityGroups=[
        Ref(SECURITY_GROUP),
        Ref(API_SERVER_SECURITY_GROUP),
        Ref(CONSUL_HTTP_API_SECURITY_GROUP)
        ],
    UserData=Base64(Join('', [
        '#cloud-config\n\n',
        'coreos:\n',
        '  update:\n',
        '    reboot-strategy: off\n',
        '  etcd2:\n',
        '    advertise-client-urls: http://$private_ipv4:2379\n',
        '    initial-advertise-peer-urls: http://$private_ipv4:2380\n',
        '    listen-client-urls: http://0.0.0.0:2379\n',
        '    listen-peer-urls: http://$private_ipv4:2380\n',
        '  units:\n',
        '    - name: update-engine.service\n',
        '      command: stop\n',
        '    - name: locksmithd.service\n',
        '      command: stop\n',
        '    - name: format-ephemeral.service\n',
        '      command: start\n',
        '      content: |\n',
        '        [Unit]\n',
        '        Description=Formats the ephemeral drive\n',
        '        After=dev-xvdb.device\n',
        '        Requires=dev-xvdb.device\n',
        '        [Service]\n',
        '        Type=oneshot\n',
        '        RemainAfterExit=yes\n',
        '        ExecStart=/usr/sbin/wipefs -f /dev/xvdb\n',
        '        ExecStart=/usr/sbin/mkfs.ext4 -F /dev/xvdb\n',
        '    - name: var-lib-docker.mount\n',
        '      command: start\n',
        '      content: |\n',
        '        [Unit]\n',
        '        Description=Mount ephemeral to /var/lib/docker\n',
        '        Requires=format-ephemeral.service\n',
        '        After=format-ephemeral.service\n',
        '        [Mount]\n',
        '        What=/dev/xvdb\n',
        '        Where=/var/lib/docker\n',
        '        Type=ext4\n',
        '    - name: docker.service\n',
        '      drop-ins:\n',
        '        - name: 10-wait-docker.conf\n',
        '          content: |\n',
        '            [Unit]\n',
        '            After=var-lib-docker.mount\n',
        '            Requires=var-lib-docker.mount\n',
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
        '            Environment="RKT_OPTS=--volume=resolv,kind=host,source=/etc/resolv.conf ',
        '--mount volume=resolv,target=/etc/resolv.conf"\n',
        '            Environment=KUBELET_VERSION=v1.2.2_coreos.0\n',
        '            ExecStartPre=/usr/bin/mkdir -p /etc/kubernetes/manifests\n\n',
        '            ExecStart=\n',
        '            ExecStart=/usr/lib/coreos/kubelet-wrapper \\\n',
        '              --api-servers=http://127.0.0.1:8080 \\\n',
        '              --allow-privileged=true \\\n',
        '              --cloud-provider=aws \\\n',
        '              --config=/etc/kubernetes/manifests\n',
        '            Restart=always\n',
        '            RestartSec=10\n',
        '    - name: kube-system.service\n',
        '      command: start\n',
        '      content: |\n',
        '        [Unit]\n',
        '        After=kubelet.service\n',
        '        Requires=kubelet.service\n\n',
        '        [Service]\n',
        '        Type=oneshot\n',
        '        ExecStart=/bin/sh -c \'while true; do curl -H "Content-Type: application/json" ',
        '-XPOST -d\\\'{"apiVersion":"v1","kind":"Namespace","metadata":{"name":"kube-system"}}\\\'',
        ' -sS "http://127.0.0.1:8080/api/v1/namespaces" && break || sleep 20; done\'\n',
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
        '          image: quay.io/coreos/hyperkube:v1.2.2_coreos.0\n',
        '          command:\n',
        '          - /hyperkube\n',
        '          - apiserver\n',
        '          - --etcd-servers=http://127.0.0.1:2379\n',
        '          - --allow-privileged=true\n',
        '          - --service-cluster-ip-range=10.3.0.0/24\n',
        '          - --secure-port=443\n',
        '          - --admission-control=NamespaceLifecycle,LimitRanger,SecurityContextDeny,',
        'ResourceQuota\n',
        '          - --runtime-config=extensions/v1beta1/deployments=true,',
        'extensions/v1beta1/daemonsets=true\n',
        '          - --external-hostname=', GetAtt(API_SERVER_LOAD_BALANCER, 'DNSName'), '\n',
        '          - --basic-auth-file=/srv/kubernetes/basic_auth.csv\n',
        '          - --cloud-provider=aws\n',
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
        '          image: quay.io/coreos/hyperkube:v1.2.2_coreos.0\n',
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
        '  - path: /etc/kubernetes/manifests/kube-controller-manager.yaml\n',
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
        '          image: quay.io/coreos/hyperkube:v1.2.2_coreos.0\n',
        '          command:\n',
        '          - /hyperkube\n',
        '          - controller-manager\n',
        '          - --master=http://127.0.0.1:8080\n',
        '          - --leader-elect=true\n',
        '          - --service-sync-period=10m\n',
        '          - --node-sync-period=5m\n',
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
        '  - path: /etc/kubernetes/manifests/kube-scheduler.yaml\n',
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
        '          image: quay.io/coreos/hyperkube:v1.2.2_coreos.0\n',
        '          command:\n',
        '          - /hyperkube\n',
        '          - scheduler\n',
        '          - --master=http://127.0.0.1:8080\n',
        '          - --leader-elect=true\n',
        '          livenessProbe:\n',
        '            httpGet:\n',
        '              host: 127.0.0.1\n',
        '              path: /healthz\n',
        '              port: 10251\n',
        '            initialDelaySeconds: 15\n',
        '            timeoutSeconds: 1\n',
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
        '            hostIP: $private_ipv4\n',
        '          - hostPort: 8301\n',
        '            containerPort: 8301\n',
        '            protocol: UDP\n',
        '            hostIP: $private_ipv4\n',
        '          - hostPort: 8500\n',
        '            containerPort: 8500\n',
        '            protocol: TCP\n',
        '            hostIP: $private_ipv4\n',
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
    LoadBalancerNames=[
        Ref(API_SERVER_LOAD_BALANCER),
        Ref(CONSUL_HTTP_API_LOAD_BALANCER)
        ],
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
    Value=Join('', ['https://', GetAtt(API_SERVER_LOAD_BALANCER, 'DNSName')]),
    ))

TEMPLATE.add_output(Output(
    'ConsulHTTPAPI',
    Value=Join('', ['http://', GetAtt(CONSUL_HTTP_API_LOAD_BALANCER, 'DNSName'), ':8500']),
    ))

if __name__ == '__main__':
    print TEMPLATE.to_json()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100
