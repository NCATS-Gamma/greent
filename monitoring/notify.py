##############
# Notify emails on build failures using the smtp server configured
#
# Email addresses to be notified can be listed as a Jenkins parameter as CSVs
##################
from greent.config import Config
import argparse
from email.mime.text import MIMEText
import smtplib


def send_mail(emails, message, subject):
    config = Config({})

    server = smtplib.SMTP(config['ROBOKOP_MAIL_SERVER'])
    server.login(config['ROBOKOP_MAIL_USERNAME'], config['ROBOKOP_MAIL_PASSWORD'])
    sender = config['ROBOKOP_DEFAULT_MAIL_SENDER']
    
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ','.join(emails)
    
    server.sendmail(sender, emails, msg.as_string())



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
     description= 'Send email notifications using robokop environment',
     formatter_class= argparse.RawDescriptionHelpFormatter   
    )
    parser.add_argument('-e', '--emails', help = 'csv list of emails with no spaces')
    parser.add_argument('-m', '--message', help= 'Message to send')
    parser.add_argument('-s', '--subject', help = 'Email subject')
    args = parser.parse_args()

    emails, message = False, False
    subject = 'ROBOKOP Jenkins'
    if args.emails :
        emails = list(map(lambda x: x.strip(), args.emails.split(',')))    
    if args.message:
        message = args.message
    if args.subject:
        subject = args.subject
    if emails and message:
        send_mail(emails, message, subject)
    else :
        print(
            "Missing arguments"
        )
