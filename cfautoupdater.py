import os, sys, requests, time, json, configparser, smtplib, logging, datetime
from email.mime.text import MIMEText

# Reading the keys from the cfauth.ini file
config = configparser.ConfigParser()
config.read('cfauth.ini')

zone_id = config.get('tokens', 'zone_id')
bearer_token = config.get('tokens', 'bearer_token')
record_id = config.get('tokens', 'record_id')
email_sender = config.get('tokens', 'email_sender')
email_password = config.get('tokens', 'email_password')
email_recipient = config.get('tokens', 'email_recipient')

# Setting up the logger (a file where it records all IP changes)
logging.basicConfig(level=logging.INFO, filename='ipchanges.log', format='%(levelname)s :: %(message)s')

# The headers we want to use
headers = {
    "Authorization": f"Bearer {bearer_token}", 
    "content-type": "application/json"
    }

email_subject = "Sean's server - Cloudflare DNS IP Updated"
email_to = [email_recipient]

check_wait_time = 300
curr_ip_wait_time = 10

def send_email(body):
    msg = MIMEText(body)
    msg['Subject'] = email_subject
    msg['From'] = email_sender
    msg['To'] = ', '.join(email_to)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
       smtp_server.login(email_sender, email_password)
       smtp_server.sendmail(email_sender, email_to, msg.as_string())

while True:
    # Getting the initial data of your A Record
    a_record_url = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}", headers=headers)
    arecordjson = a_record_url.json()

    # This is the current IP that your chosen A record has been set to on Cloudflare
    current_set_ip = arecordjson['result']['content']
    
    current_actual_ip = current_set_ip
    
    # This loop checks your live IP every 5 minutes to make sure that it's the same one as set in your DNS record
    while True:
        currentip = requests.get("https://api.ipify.org?format=json") # Then it checks if your IP is still the same or not.
        ipcheck_status = currentip.status_code

        # Handling any API errors AGAIN
        while ipcheck_status != 200:
            time.sleep(curr_ip_wait_time)
            currentip = requests.get("https://api.ipify.org?format=json")
            ipcheck_status = currentip.status_code

        current_actual_ip = currentip.json()['ip']
        
        if current_actual_ip != current_set_ip:
            break
        
        time.sleep(check_wait_time) # Wait for 300 seconds (5 minutes)

    # The "Payload" is what we want to change in the DNS record JSON (in this case, it's our IP)
    payload = {"content": current_actual_ip}

    # Change the IP using a PATCH request
    requests.patch(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}", headers=headers, data=json.dumps(payload))
    
    # Get the time of the IP change
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # LOG THE CHANGE
    logging.info(f"{now} - IP change from {current_set_ip} to {current_actual_ip}")


    # Sends an email to you to let you know everything has been updated.
    message = f"The server's IP has changed from {current_set_ip} to {current_actual_ip}. The DNS records have been updated."
    send_email(message)
    
    time.sleep(check_wait_time)
