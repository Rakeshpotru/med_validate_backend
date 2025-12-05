import logging
import httpx
import json

from app.config import config

logger = logging.getLogger(__name__)

class APIResponseError(Exception):
    pass

async def send_simple_email(to: str, subject: str, body: str):
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {config.SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "personalizations": [{
            "to": [{"email": to}],
            "subject": subject
        }],
        "from": {"email": config.EMAIL_FROM},
        "content": [{
            "type": "text/html",
            "value": body
        }]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, content=json.dumps(data))
            response.raise_for_status()
            logger.debug(f"SendGrid response status: {response.status_code}")
            return response
        except httpx.HTTPStatusError as err:
            logger.error(f"SendGrid API error: {err.response.text}")
            raise APIResponseError(f"SendGrid error {err.response.status_code}") from err