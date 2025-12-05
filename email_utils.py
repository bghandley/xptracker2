import os
import smtplib
from email.message import EmailMessage
import streamlit as st

def _get_smtp_config():
    # Prefer Streamlit secrets
    cfg = {}
    if hasattr(st, 'secrets') and 'smtp' in st.secrets:
        cfg = dict(st.secrets['smtp'])
    else:
        cfg['host'] = os.environ.get('SMTP_HOST')
        cfg['port'] = int(os.environ.get('SMTP_PORT', 0)) if os.environ.get('SMTP_PORT') else None
        cfg['user'] = os.environ.get('SMTP_USER')
        cfg['password'] = os.environ.get('SMTP_PASSWORD')
        cfg['from'] = os.environ.get('SMTP_FROM')
    return cfg


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Send a simple text email. Returns True on success, False otherwise."""
    cfg = _get_smtp_config()
    host = cfg.get('host')
    port = cfg.get('port')
    user = cfg.get('user')
    password = cfg.get('password')
    from_addr = cfg.get('from') or user

    if not host or not port:
        st.error('SMTP not configured. Set st.secrets["smtp"] or SMTP_HOST/SMTP_PORT env vars.')
        return False

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_address
    msg.set_content(body)

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port) as smtp:
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as smtp:
                smtp.ehlo()
                try:
                    smtp.starttls()
                    smtp.ehlo()
                except Exception:
                    # STARTTLS may not be available; continue
                    pass
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False
