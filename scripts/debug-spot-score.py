#!/usr/bin/env python3
import boto3
import json

ec2 = boto3.client('ec2', region_name='ap-southeast-2')
response = ec2.get_spot_placement_scores(
    InstanceTypes=["m5.large", "c5.large"],
    TargetCapacity=1,
    SingleAvailabilityZone=False
)

print(json.dumps(response, indent=2, default=str))
