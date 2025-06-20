import json
from discord_webhook import DiscordWebhook, DiscordEmbed
import requests
from botocore.config import Config
import boto3
import time

def get_second():
    return int(str(int(time.time()))[-1]) # see this logic ? its so complex. yet so simple

logo_link = "https://raw.githubusercontent.com/SurajBhari/ec2_maintainer/main/256_ec2_maintainer.png"
project_name = "Ec2 Maintainer"
count = 1
last_second = get_second()

continous_down = {} # store continous down instances and the count 
config = json.load(open('config.json', "r"))

discord_message_dict = {} # store discord messages so that we dont spam the maintainer with messages
# notify all of the discord that the maintainer is starting 
for instance in config.keys():
    if not config[instance]['discord']:
        continue
    embed = DiscordEmbed(
        title=f"{instance} is starting!", 
        color=0x00ab00,
        description=f"{instance} is starting! Checking every {config[instance]['interval']} seconds..."
    )
    webhook = DiscordWebhook(
        username = project_name, 
        avatar_url=logo_link, 
        url=config[instance]['discord'], 
        embeds=[embed]
    )
    response = webhook.execute()
    
while True:
    while last_second == get_second():
        time.sleep(0.1)
    last_second = get_second()
    config = json.load(open('config.json', "r"))
    for instance in config.keys():
        if count % config[instance]['interval'] != 0:
            print(f"{count}. Not time to check {instance}...")
            continue # Skip if not time to check
        print(f"Checking {instance}...")
        location = config[instance]['location']
        url = location['url']
        headers = location['headers']
        tolerance = config[instance]['tolerance']
        timeout = location['timeout']
        ok = False
        while tolerance > 0:
            time.sleep(1)
            try:
                response = requests.get(url, headers=headers, timeout=timeout)
            except Exception as e:
                print(f"{instance} is down!")
                tolerance -= 1
                continue
            if response.status_code == location["response_code"]:
                print(f"{instance} Responded with correct code!")
                if instance in discord_message_dict:
                    webhook = discord_message_dict[instance]
                else:
                    webhook = DiscordWebhook(
                        username = project_name, 
                        avatar_url=logo_link, 
                        url=config[instance]['discord'], 
                    )
                webhook.content = f"<t:{int(time.time())}:R> | {instance} is up! Response code: {response.status_code} "
                if instance in discord_message_dict:
                    webhook.edit() # if we already have a message, edit it
                else:
                    webhook.execute()
                webhook.execute()
                discord_message_dict[instance] = webhook
                ok = True
                break
            print(f"{instance} said {response.status_code}!")
            tolerance -= 1
        if continous_down.get(instance, 0) >= config[instance]['max_down']:
            continue # stop caring if its been down for so long so that i can actually do stuff and fix it 
        if ok:
            continous_down[instance] = 0
            continue
        if config[instance]['discord']:
            embed = DiscordEmbed(
                title=f"{url} is down!", 
                color=0xf54242,
                description=f"{instance} is down! Restarting now..."
            )
            webhook = DiscordWebhook(
                username = project_name, 
                avatar_url=logo_link, 
                url=config[instance]['discord'], 
                embeds=[embed]
            )
            response = webhook.execute()
            if instance in discord_message_dict:
                del discord_message_dict[instance] # remove the message so that we can send a new one
        continous_down[instance] = continous_down.get(instance, 0) + 1
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
        if config[instance]['discord']:
            embed = DiscordEmbed(
                title=f"{instance} has been restarted!", 
                color=0x00ab00,
            )
            webhook = DiscordWebhook(
                username = project_name,
                avatar_url=logo_link,
                url=config[instance]['discord'], 
                embeds=[embed]
            )
            response = webhook.execute()

    count += 1

