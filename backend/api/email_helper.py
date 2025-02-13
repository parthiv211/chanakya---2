from config import ses_email_client
from model import db
from model.db import get_session
from datetime import datetime
from sqlalchemy import select, func

def sendEmail(recipient, BODY_HTML, subject):
    # recipient.append("hello@itmtb.com")
    if 'ananttanted@tigc.in' in recipient:
        recipient.remove('ananttanted@tigc.in')
    if 'muneeshkumar.p@tigc.in' in recipient:
        recipient.remove('muneeshkumar.p@tigc.in')
    if 'harshini.sh@tigc.in' in recipient:
        recipient.remove('harshini.sh@tigc.in')
    if 'seema.bhat@tigc.in' in recipient:
        recipient.remove('seema.bhat@tigc.in')
    if 'pinkyroy@tigc.in' in recipient:
        recipient.remove('pinkyroy@tigc.in')
    if 'alka.dembla@tigc.in' in recipient:
        recipient.remove('alka.dembla@tigc.in')
    if 'satish.kr@tigc.in' in recipient:
        recipient.remove('satish.kr@tigc.in')


    print(recipient, subject)
    SENDER = "Chanakya <hello@itmtb.com>"
    CONFIGURATION_SET = "my-first-configuration-set"
    SUBJECT = subject
    BODY_TEXT = ("Please open the mail in supported browser")
    CHARSET = "UTF-8"
    try:
        response = ses_email_client.send_email(
            Destination={
                'ToAddresses': recipient,
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
            ConfigurationSetName=CONFIGURATION_SET,
        )
    except Exception as e:
        print(e.response['Error']['Message'])
        return 0
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
        return response['MessageId']

async def get_recipents(new_status):
    recipient = []
    async with get_session() as s:
        if new_status.lower() == 'approved':
            query = select(db.Department).where(func.lower(db.Department.name) == func.lower('Admin'))
        else:
            query = select(db.Department).where(func.lower(db.Department.name) == func.lower(new_status))
        result = (await s.execute(query)).unique()
        department_unique = result.scalars().all()
        department=[department.id for department in department_unique]
        if not department:
            print(f"Error: Department with name '{new_status}' not found.")
            return
        query2 = select(db.User).where(db.User.department_id.in_(department))
        result2 = await s.execute(query2)
        users = result2.unique().scalars().all()
        if not users:
            print(f"Error: No users found for department '{new_status}'.")
            return
        recipient = [user.email for user in users]
    return recipient

async def send_email_status_update(old_status, new_status, style_id, product_id, edited_by_email, timestamp):
    if not old_status or not new_status or not product_id or not edited_by_email or not timestamp or not style_id:
        print("Error: Missing required parameters.")
        return
    
    if new_status == 'Design':
        return
        
    recipient = await get_recipents(new_status)
    if not recipient:
        print("Error: No recipients found.")
        return
    # if "archit.jain@itmtb.com" not in recipient:
    #     recipient.append("archit.jain@itmtb.com")
    print(recipient)

    try:
        with open('./email_templates/status_update.html', 'r', encoding='utf-8') as file:
            body_html = file.read()
    except FileNotFoundError:
        print("Error: 'status_update.html' file not found.")
        return
    placeholders = {
        'style_id': style_id,
        'product_id': product_id,
        'old_status': old_status,
        'new_status': new_status,
        'edited_by_email': edited_by_email,
        'timestamp': datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%b %d, %Y %I:%M %p")
    }
    try:
        body_html = body_html.format(**placeholders)
    except KeyError as e:
        print(f"Error: Missing placeholder. Details: {e}")
        return
    
    subject = f"Status Update: Style ID {style_id}"
    # recipient = ["archit.jain@itmtb.com"]
    # body_html = "Please ignore the previous mail as it was a test mail!"
    message_id = sendEmail(recipient, body_html, subject)
    if message_id:
        print(f"Email sent successfully! Message ID: {message_id}")
    else:
        print("Failed to send email.")
    
    return message_id

async def send_email_reject_product(old_status, new_status, style_id, product_id, rejected_by_email, timestamp, reject_reason):
    if not old_status or not new_status or not product_id or not rejected_by_email or not timestamp or not style_id or not reject_reason:
        print("Error: Missing required parameters.")
        return

    if new_status == 'Design':
        return

    recipient = await get_recipents(new_status)
    if not recipient:
        print("Error: No recipients found.")
        return
    # if "archit.jain@itmtb.com" not in recipient:
    #     recipient.append("archit.jain@itmtb.com")
    print(recipient)

    try:
        with open('./email_templates/product_reject.html', 'r', encoding='utf-8') as file:
            body_html = file.read()
    except FileNotFoundError:
        print("Error: 'product_reject.html' file not found.")
        return
    placeholders = {
        'style_id': style_id,
        'product_id': product_id,
        'old_status': old_status,
        'new_status': new_status,
        'rejected_by_email': rejected_by_email,
        'timestamp': datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%b %d, %Y %I:%M %p"),
        'rejection_reason': reject_reason
    }
    try:
        body_html = body_html.format(**placeholders)
    except KeyError as e:
        print(f"Error: Missing placeholder. Details: {e}")
        return
    
    subject = f"Product Rejected: Style ID {style_id}"
    # recipient = ["archit.jain@itmtb.com"]
    message_id = sendEmail(recipient, body_html, subject)
    if message_id:
        print(f"Email sent successfully! Message ID: {message_id}")
    else:
        print("Failed to send email.")
    
    return message_id

async def send_bulk_status_update_notification(old_status, new_status, style_id, edited_by_email, timestamp):
    if not old_status or not new_status or not edited_by_email or not timestamp or not style_id:
        print("Error: Missing required parameters.")
        return

    if new_status == 'Design':
        return

    recipient = await get_recipents(new_status)
    if not recipient:
        print("Error: No recipients found.")
        return
    # if "archit.jain@itmtb.com" not in recipient:
    #     recipient.append("archit.jain@itmtb.com")
    print(recipient)

    try:
        with open('./email_templates/bulk_update.html', 'r', encoding='utf-8') as file:
            body_html = file.read()
    except FileNotFoundError:
        print("Error: 'bulk_update.html' file not found.")
        return
    placeholders = {
        'style_id': style_id,
        'old_status': old_status,
        'new_status': new_status,
        'edited_by_email': edited_by_email,
        'timestamp': datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%b %d, %Y %I:%M %p")
    }
    try:
        body_html = body_html.format(**placeholders)
    except KeyError as e:
        print(f"Error: Missing placeholder. Details: {e}")
        return
    
    subject = f"Status Bulk Update: Style IDs {style_id}"
    # recipient = ["archit.jain@itmtb.com"]
    # body_html = "Please ignore the previous mail as it was a test mail!"
    message_id = sendEmail(recipient, body_html, subject)
    if message_id:
        print(f"Email sent successfully! Message ID: {message_id}")
    else:
        print("Failed to send email.")
    
    return message_id

async def send_new_product_add_email(new_status, style_id, product_id, edited_by_email, timestamp):
    if not new_status or not product_id or not edited_by_email or not timestamp or not style_id:
        print("Error: Missing required parameters.")
        return

    if new_status == 'Design':
        return

    recipient = await get_recipents(new_status)
    if not recipient:
        print("Error: No recipients found.")
        return
    # if "archit.jain@itmtb.com" not in recipient:
    #     recipient.append("archit.jain@itmtb.com")
    print(recipient)

    try:
        with open('./email_templates/add_product.html', 'r', encoding='utf-8') as file:
            body_html = file.read()
    except FileNotFoundError:
        print("Error: 'add_product.html' file not found.")
        return
    placeholders = {
        'style_id': style_id,
        'product_id': product_id,
        'new_status': new_status,
        'edited_by_email': edited_by_email,
        'timestamp': datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%b %d, %Y %I:%M %p")
    }
    try:
        body_html = body_html.format(**placeholders)
    except KeyError as e:
        print(f"Error: Missing placeholder. Details: {e}")
        return
    
    subject = f"New Product Added: Style ID {style_id}"
    # recipient = ["archit.jain@itmtb.com"]
    
    message_id = sendEmail(recipient, body_html, subject)
    if message_id:
        print(f"Email sent successfully! Message ID: {message_id}")
    else:
        print("Failed to send email.")
    
    return message_id