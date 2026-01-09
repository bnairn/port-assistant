"""Email sender utility for daily briefings"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


def send_briefing_email(
    briefing_markdown: str,
    recipient_email: str,
    subject: str = "Your Daily Briefing",
    sender_email: Optional[str] = None,
    sender_password: Optional[str] = None
) -> bool:
    """
    Send briefing as HTML email using Gmail SMTP

    Args:
        briefing_markdown: The markdown briefing content
        recipient_email: Email address to send to
        subject: Email subject line
        sender_email: Gmail address (defaults to env var)
        sender_password: Gmail app password (defaults to env var)

    Returns:
        True if sent successfully, False otherwise
    """
    sender_email = sender_email or os.getenv("SENDER_EMAIL")
    sender_password = sender_password or os.getenv("SENDER_APP_PASSWORD")

    if not sender_email or not sender_password:
        raise ValueError("SENDER_EMAIL and SENDER_APP_PASSWORD must be set in .env")

    try:
        # Convert markdown to HTML (basic conversion)
        html_content = markdown_to_html(briefing_markdown)

        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = recipient_email

        # Add plain text version (fallback)
        text_part = MIMEText(briefing_markdown, "plain")
        message.attach(text_part)

        # Add HTML version
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        # Send via Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(message)

        print(f"✅ Email sent successfully to {recipient_email}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        return False


def markdown_to_html(markdown: str) -> str:
    """
    Convert markdown to HTML for email

    Uses basic markdown conversion. For production, consider using
    a library like markdown2 or mistune.
    """
    html = markdown

    # Basic conversions
    import re

    # Headers
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)

    # Bold
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)

    # Links
    html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" style="color: #3498db;">\1</a>', html)

    # Line breaks (markdown uses two spaces + newline or two newlines)
    html = html.replace('  \n', '<br>\n')
    html = re.sub(r'\n\n+', '</p><p>', html)

    # Lists
    html = re.sub(r'^\- (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)

    # Remove horizontal rules entirely
    html = html.replace('---', '')

    # Wrap in HTML template with compact styling and page numbers
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @media print {{
                @page {{
                    margin: 0.5in;
                    @bottom-center {{
                        content: "Page " counter(page) " of " counter(pages);
                    }}
                }}
            }}

            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.35;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 15px;
                background-color: #f5f5f5;
                font-size: 13px;
            }}
            .container {{
                background-color: white;
                padding: 20px 25px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 6px;
                margin-bottom: 12px;
                font-size: 22px;
            }}
            h2 {{
                color: #2c3e50;
                margin-top: 15px;
                margin-bottom: 6px;
                font-size: 16px;
                border-bottom: 1px solid #e0e0e0;
                padding-bottom: 3px;
            }}
            h3 {{
                font-size: 14px;
                margin-top: 10px;
                margin-bottom: 4px;
            }}
            p {{
                margin: 6px 0;
            }}
            ul {{
                margin: 6px 0;
                padding-left: 20px;
            }}
            li {{
                margin: 3px 0;
                line-height: 1.4;
            }}
            a {{
                color: #3498db;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .metadata {{
                color: #7f8c8d;
                font-size: 0.85em;
                margin: 4px 0 8px 0;
            }}
            .page-footer {{
                text-align: center;
                color: #7f8c8d;
                font-size: 11px;
                margin-top: 20px;
                padding-top: 10px;
                border-top: 1px solid #e0e0e0;
            }}
            strong {{
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {html}
            <div class="page-footer">
                Daily Briefing | Generated with Port Assistant
            </div>
        </div>
    </body>
    </html>
    """

    return html_template


if __name__ == "__main__":
    # Test email sending
    test_markdown = """# Test Daily Briefing

**Generated at:** 2026-01-08

---

## Weather

**Boston, Massachusetts**
Currently 41°F, overcast clouds.

---

## Test Section

This is a test email with **bold text** and a [link](https://example.com).

- Item 1
- Item 2
- Item 3
"""

    recipient = os.getenv("RECIPIENT_EMAIL", "your-email@example.com")
    send_briefing_email(test_markdown, recipient, subject="Test Daily Briefing")
