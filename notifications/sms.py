from django.conf import settings

def send_sms(to_number: str, message: str) -> bool:
    """
    Sends an SMS via Twilio. Returns True on success, False on failure.
    Gracefully skips if Twilio credentials are not configured.
    """
    if not all([
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN,
        settings.TWILIO_FROM_NUMBER,
    ]):
        return False

    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_FROM_NUMBER,
            to=to_number,
        )
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Twilio SMS failed: {e}")
        return False
