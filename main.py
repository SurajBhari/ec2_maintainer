import json
from discord_webhook import DiscordWebhook
import requests
from botocore.config import Config
import boto3

count = 1
while True:
    config = json.load(open('config.json', "r"))
    for instance in config.keys():
        if count % config[instance]['interval'] != 0:
            print("Not time to check")
            continue # Skip if not time to check
        print(f"Checking {instance}...")
        location = config[instance]['location']
        url = location['url']
        headers = location['headers']
        tolerance = config[instance]['tolerance']
        timeout = location['timeout']
        ok = False
        while tolerance > 0:
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == location["response_code"]:
                print(f"{instance} Responded with correct code!")
                ok = True
                break
            print(f"{instance} said {response.status_code}!")
            tolerance -= 1
        if ok:
            continue
        if config[instance]['discord']:
            webhook = DiscordWebhook(url=config[instance]['discord'], content=f"{instance} is down!")
            response = webhook.execute()
        ec2 = config[instance]['ec2']
        ec2 = boto3.client(
            'ec2', 
            region_name=ec2['region'], 
            aws_access_key_id=ec2['aws_access_key_id'], 
            aws_secret_access_key=ec2['aws_secret_access_key']
        )
        ec2.stop_instances(InstanceIds=[instance])
        waiter = ec2.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=[instance])
        ec2.start_instances(InstanceIds=[instance])
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance])
        webhook.content = f"{instance} has been restarted!"
        response = webhook.execute()

    count += 1

