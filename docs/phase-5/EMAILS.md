# Email and SMS Notifications

## Goal
Establish a automated messaging engine sending transactional HTML emails (e.g., license expiration alerts, maintenance reminders) via django-anymail and instant SMS warnings via Twilio.

## Scope
- Central integration with django-anymail (SendGrid or Mailgun) for transactional emails.
- Twilio REST API integration for SMS dispatch.
- Custom Django management command to evaluate credential compliance.
- Support for HTML email rendering with plain-text fallback options.

## Responsibilities
- **Developer**: Set up external APIs, handle credentials, write the management command.
- **Safety Officer**: Receives automated daily digest of all expiring credentials.
- **Driver**: Receives direct SMS warnings when license credentials face expiration.

## Django App(s)
`notifications`

## Files to Create / Modify
```
transit_project/
  settings.py         # Configure Anymail and Twilio credentials
notifications/
  __init__.py
  apps.py
  utils.py            # Low-level SMS and Email dispatcher utilities
  management/
    commands/
      send_compliance_alerts.py # CLI runner to check expirations
  templates/
    notifications/
      email/
        license_warning.html # HTML template for compliance emails
```

## Dependencies
- django-anymail and Twilio SDK packages.
- Phase 5 `documents` app (for document tracking).
- Phase 2 `drivers` app (for contact data).

## Business Rules
1. **Asynchronous Execution**: External APIs (Anymail or Twilio) must never run synchronously within views to avoid locking up web server threads. Always utilize background management commands or Celery tasks.
2. **Frequency Controls**: Warning alerts are generated only when license expiry is less than 30 days away. The system must restrict duplicate notifications to avoid spamming the same recipient multiple times.
3. **Secret Security**: No API tokens, passwords, or usernames can be hardcoded. Retrieve credentials exclusively from system environment variables.
4. **Fallback Handling**: If an HTML email fails to render or load, the system must dispatch a plain-text version fallback.

## Implementation Steps

### Step 1 — Add settings Configuration
```python
# transit_project/settings.py
import os

# Anymail configuration (e.g., using SendGrid)
ANYMAIL = {
    "SENDGRID_API_KEY": os.getenv("SENDGRID_API_KEY"),
}
EMAIL_BACKEND = "anymail.backends.sendgrid.EmailBackend"
DEFAULT_FROM_EMAIL = "alerts@transitops.com"

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
```

### Step 2 — Implement Messaging Helpers
```python
# notifications/utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from twilio.rest import Client

def send_html_email(subject, recipient_email, template_name, context):
    html_content = render_to_string(template_name, context)
    text_content = f"Reminder: {subject}. Please log in to TransitOps."
    
    msg = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [recipient_email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()

def send_sms_notification(to_phone, message_body):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    client.messages.create(
        body=message_body,
        from_=settings.TWILIO_PHONE_NUMBER,
        to=to_phone
    )
```

### Step 3 — Write the Management Command
```python
# notifications/management/commands/send_compliance_alerts.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from documents.models import Document
from notifications.utils import send_html_email, send_sms_notification

class Command(BaseCommand):
    help = "Dispatches warning notifications for driver licenses expiring within 30 days."

    def handle(self, *args, **options):
        now = timezone.now().date()
        warning_limit = now + timezone.timedelta(days=30)
        
        # Query expiring documents
        expiring_docs = Document.objects.filter(
            category="license",
            expiry_date__range=(now, warning_limit)
        )

        for doc in expiring_docs:
            if doc.driver:
                driver = doc.driver
                recipient_email = driver.user.email
                
                # Send email
                send_html_email(
                    subject="License Expiry Warning",
                    recipient_email=recipient_email,
                    template_name="notifications/email/license_warning.html",
                    context={"driver": driver, "days_left": (doc.expiry_date - now).days}
                )

                # Send SMS
                if driver.contact_number:
                    send_sms_notification(
                        to_phone=driver.contact_number,
                        message_body=f"TransitOps: Your license expires in {(doc.expiry_date - now).days} days. Please update."
                    )
                    
        self.stdout.write(self.style.SUCCESS(f"Successfully processed {expiring_docs.count()} documents."))
```

## Success Scenario
1. The cron job runs `python manage.py send_compliance_alerts`.
2. The database has one record for a driver whose license expires in 12 days.
3. The server locates the record, compiles the template variables, and dispatches the HTML alert.
4. The driver receives both an email in their inbox and an SMS message on their phone.

## Definition of Done
- [ ] Email configurations utilize `django-anymail` backend wrapper.
- [ ] Command executes safely from the terminal without breaking.
- [ ] SMS helper formats destination phone numbers correctly before sending.
- [ ] API keys are extracted from environment variables.
- [ ] Fallback plaintext strings are supplied on all HTML mail calls.

## AI Instructions
- Wrap external communication calls (Twilio client instantiation, Anymail send calls) inside `try-except` blocks to prevent network timeouts from crashing execution.
- Utilize standard E.164 formats for SMS numbers to ensure cross-border delivery.
- Set up logging trackers to record failed mail attempts for audit purposes.
