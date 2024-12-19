import json
import os

import requests

from leettools.common.emailer.emailer import AbstractEmailer
from leettools.common.logging import logger
from leettools.settings import SystemSettings


class EmailerMailgun(AbstractEmailer):
    def __init__(self, settings: SystemSettings) -> None:
        self.settings = settings

        self.MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY")
        self.MAILGUN_URI = os.environ.get("MAILGUN_URI")
        self.DEFAULT_MAILGUN_SENDER = os.environ.get("DEFAULT_MAILGUN_SENDER")

    def send_email(self, to: str, subject: str, body: str) -> None:
        mailgun_uri = self.MAILGUN_URI
        mailgun_api_key = self.MAILGUN_API_KEY
        mailgun_sender = self.DEFAULT_MAILGUN_SENDER
        variables = {}
        variables["body"] = body
        variables_json_string = json.dumps(variables)
        try:

            response = requests.post(
                mailgun_uri,
                auth=("api", mailgun_api_key),
                data={
                    "from": mailgun_sender,
                    "to": to,
                    "subject": subject,
                    "template": "leettools-post",
                    "h:X-Mailgun-Variables": variables_json_string,
                },
            )
            logger().info(f"Email sent: {response.text}")
            return True
        except requests.exceptions.RequestException as e:
            logger().error(f"Failed to send email to {to}: {e}")
            return False
