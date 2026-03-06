import boto3

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')

    # Get all snapshots owned by this account
    snapshots = ec2.describe_snapshots(OwnerIds=['self'])['Snapshots']

    # Get all running EC2 instances
    instances_response = ec2.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )

    active_instance_ids = set()

    for reservation in instances_response['Reservations']:
        for instance in reservation['Instances']:
            active_instance_ids.add(instance['InstanceId'])

    for snapshot in snapshots:
        snapshot_id = snapshot['SnapshotId']
        volume_id = snapshot.get('VolumeId')

        try:
            volume_response = ec2.describe_volumes(VolumeIds=[volume_id])
            attachments = volume_response['Volumes'][0]['Attachments']

            # CASE 1: Volume exists but not attached to any running EC2 instance
            if not attachments or attachments[0]['InstanceId'] not in active_instance_ids:
                ec2.delete_snapshot(SnapshotId=snapshot_id)
                print(f"Deleted snapshot {snapshot_id} because EC2 instance was deleted or volume not attached.")

        except ec2.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'InvalidVolume.NotFound':
                
                # CASE 2: Volume itself was deleted
                ec2.delete_snapshot(SnapshotId=snapshot_id)
                print(f"Deleted snapshot {snapshot_id} because the volume was deleted.")
