import smtplib
from email.message import EmailMessage
import os

EMAIL = "madambakamn@gmail.com"
APP_PASSWORD = "yreuaqegboxdxmdp"  # no spaces

def sendmail(to, subject, body):
    msg = EmailMessage()
    msg['From'] = EMAIL
    msg['To'] = to
    msg['Subject'] = subject
    msg.set_content(body)

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(EMAIL, APP_PASSWORD)
    server.send_message(msg)
    server.quit()
