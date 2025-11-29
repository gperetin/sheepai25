from os import environ
from logging import getLogger

import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

from dotenv import load_dotenv

load_dotenv()

log = getLogger(__name__)


def send(
    recipient: str,
    subject: str,
    content: str,
):
    """
    Send a html-only email using Amazon SES

    :param recipient: The email address of the recipient
    :param subject: The subject of the email
    :param body_html: The body of the email in HTML format
    """


    AWS_ACCESS_KEY_ID = environ.get("AWS_ACCESS_KEY_ID")
    AWS_REGION = environ.get("AWS_REGION")
    AWS_SECRET_ACCESS = environ.get("AWS_SECRET_ACCESS")
    FROM_EMAIL = environ.get("FROM_EMAIL")

    if not AWS_ACCESS_KEY_ID or not AWS_REGION or not AWS_SECRET_ACCESS or not FROM_EMAIL:
        raise ValueError("AWS credentials or FROM_EMAIL are not set in environment variables.")

    # Initialize a session using Amazon SES
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS,
        region_name=AWS_REGION,
    )

    # Create an SES client
    ses = session.client("ses")

    # Try to send the email
    try:
        ses.send_email(
            Source=FROM_EMAIL,
            Destination={
                "ToAddresses": [recipient],
            },
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": content, "Charset": "UTF-8"},
                },
            },
        )
        log.info(f"Sent '{subject}' to {recipient}")
    except (NoCredentialsError, PartialCredentialsError) as e:
        log.error(f"Error authenticating to AWS: {e}", exc_info=True)
    except Exception as e:
        log.error(f"Error sending email to {recipient}: {e}", exc_info=True)
