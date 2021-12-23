#!/bin/bash
VERSION=4.3.6
export COMMUNITY_TEMPLATE=http://neo4j-cloudformation.s3.amazonaws.com/neo4j-community-standalone-stack-$VERSION.json
export STACKNAME=neo4j-comm-$(echo $VERSION | sed s/[^A-Za-z0-9]/-/g)
export INSTANCE=r4.large
export REGION=us-east-1
export SSHKEY=cloudformation
aws cloudformation create-stack \
   --stack-name $STACKNAME \
   --region $REGION \
   --template-url $COMMUNITY_TEMPLATE \
   --parameters ParameterKey=InstanceType,ParameterValue=$INSTANCE \
     ParameterKey=NetworkWhitelist,ParameterValue=0.0.0.0/0 \
     ParameterKey=Password,ParameterValue=s00pers3cret \
     ParameterKey=SSHKeyName,ParameterValue=$SSHKEY \
     ParameterKey=VolumeSizeGB,ParameterValue=100 \
     ParameterKey=VolumeType,ParameterValue=gp2 \
     --capabilities CAPABILITY_NAMED_IAM