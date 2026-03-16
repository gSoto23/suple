import httpx
from app.core.config import settings
from app.core.logger import app_logger as logger

class WhatsAppClient:
    def __init__(self):
        self.token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.base_url = f"https://graph.facebook.com/v17.0/{self.phone_number_id}/messages"
        self.base_graph_url = "https://graph.facebook.com/v17.0"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def get_templates(self):
        """
        Fetch approved templates from Meta WhatsApp Business Account.
        """
        url = f"{self.base_graph_url}/{settings.WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates?limit=100"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            try:
                response.raise_for_status()
                return response.json().get("data", [])
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                logger.error(f"WhatsApp API Template Fetch Error: {error_detail}")
                from fastapi import HTTPException
                raise HTTPException(status_code=e.response.status_code, detail=f"WhatsApp API Error: {error_detail}")

    async def send_message(self, to: str, content: str, message_type: str = "text"):
        """
        Send a message to a WhatsApp user.
        Ensures '506' prefix is added to the phone number if missing.
        """
        # Ensure country prefix
        if not to.startswith(settings.COUNTRY_PHONE_CODE):
            to = f"{settings.COUNTRY_PHONE_CODE}{to}"

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",  # Default to text for now, extendable later
            "text": {"body": content}
        }

        # Handle image type if needed later
        if message_type == "image":
            payload["type"] = "image"
            payload["image"] = {"link": content}
            del payload["text"]

        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=self.headers)
            try:
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                logger.error(f"WhatsApp API Error: {error_detail}")
                from fastapi import HTTPException
                raise HTTPException(status_code=e.response.status_code, detail=f"WhatsApp API Error: {error_detail}")

    async def send_template_message(self, to: str, template_name: str, language_code: str = "es", components: list = None):
        """
        Send a pre-approved template message to a WhatsApp user.
        components should be formatted according to Meta's API, e.g:
        [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "Customer Name"}
                ]
            }
        ]
        """
        # Ensure country prefix
        if not to.startswith(settings.COUNTRY_PHONE_CODE):
            to = f"{settings.COUNTRY_PHONE_CODE}{to}"

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        if components is not None and len(components) > 0:
            payload["template"]["components"] = components

        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=self.headers)
            try:
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                logger.error(f"WhatsApp API Template Error: {error_detail}")
                from fastapi import HTTPException
                raise HTTPException(status_code=e.response.status_code, detail=f"WhatsApp API Error: {error_detail}")

    async def send_interactive_buttons(self, to: str, body_text: str, buttons: list[dict]):
        """
        Send an interactive message with up to 3 buttons.
        buttons should be a list of dicts: [{"id": "btn_1", "title": "Yes"}, ...]
        """
        if not to.startswith(settings.COUNTRY_PHONE_CODE):
            to = f"{settings.COUNTRY_PHONE_CODE}{to}"

        # WhatsApp API requires buttons to be formatted in a specific way
        action_buttons = []
        for btn in buttons[:3]: # Max 3 buttons
            action_buttons.append({
                "type": "reply",
                "reply": {
                    "id": btn.get("id"),
                    "title": btn.get("title")[:20] # WhatsApp limit is usually 20 chars
                }
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": body_text
                },
                "action": {
                    "buttons": action_buttons
                }
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=self.headers)
            try:
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                logger.error(f"WhatsApp API Interactive Error: {error_detail}")
                from fastapi import HTTPException
                raise HTTPException(status_code=e.response.status_code, detail=f"WhatsApp API Error: {error_detail}")

    async def send_interactive_list(self, to: str, body_text: str, button_text: str, sections: list[dict]):
        """
        Send an interactive list message.
        sections should be a list of dicts: [{"title": "Section Title", "rows": [{"id": "row_1", "title": "Row Title", "description": "Row desc"}]}]
        """
        if not to.startswith(settings.COUNTRY_PHONE_CODE):
            to = f"{settings.COUNTRY_PHONE_CODE}{to}"

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": body_text
                },
                "action": {
                    "button": button_text[:20],
                    "sections": sections
                }
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=self.headers)
            try:
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                logger.error(f"WhatsApp API List Error: {error_detail}")
                from fastapi import HTTPException
                raise HTTPException(status_code=e.response.status_code, detail=f"WhatsApp API Error: {error_detail}")

    async def get_media_url(self, media_id: str):
        """
        Get the temporary URL for a media object.
        """
        url = f"https://graph.facebook.com/v17.0/{media_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("url")

    async def download_media(self, media_url: str):
        """
        Download binary content from WhatsApp Media URL.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(media_url, headers=self.headers)
            response.raise_for_status()
            return response.content

    async def upload_media(self, file_content: bytes, mime_type: str, filename: str):
        """
        Upload media to Meta to get a media_id for sending.
        """
        url = f"https://graph.facebook.com/v17.0/{self.phone_number_id}/media"
        
        files = {
            'file': (filename, file_content, mime_type)
        }
        data = {
            'messaging_product': 'whatsapp'
        }
        
        # We don't use self.headers for multipart/form-data because httpx handles the boundary
        auth_headers = {
            "Authorization": f"Bearer {self.token}"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=auth_headers, data=data, files=files)
            try:
                response.raise_for_status()
                return response.json().get("id")
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                logger.error(f"WhatsApp API Media Upload Error: {error_detail}")
                from fastapi import HTTPException
                raise HTTPException(status_code=e.response.status_code, detail=f"WhatsApp Media Upload Error: {error_detail}")

    async def send_media_message(self, to: str, media_id: str, media_type: str = "image", filename: str = None, caption: str = None):
        """
        Send a media message (image or document) using a pre-uploaded media_id.
        media_type can be 'image', 'document', 'audio', 'video'.
        """
        if not to.startswith(settings.COUNTRY_PHONE_CODE):
            to = f"{settings.COUNTRY_PHONE_CODE}{to}"

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": media_type,
            media_type: {
                "id": media_id
            }
        }
        
        if filename and media_type == "document":
            payload[media_type]["filename"] = filename
            
        if caption and media_type in ["image", "video", "document"]:
            payload[media_type]["caption"] = caption

        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=self.headers)
            try:
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                logger.error(f"WhatsApp API Send Media Error: {error_detail}")
                from fastapi import HTTPException
                raise HTTPException(status_code=e.response.status_code, detail=f"WhatsApp Send Media Error: {error_detail}")

whatsapp_client = WhatsAppClient()
