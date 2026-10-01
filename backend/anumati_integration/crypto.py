"""
Symmetric encryption for the one secret SRIP has to persist because
Anumati's current API demands it: an institution's Anumati password (see
users/models.py, Institution.set_anumati_password). Used nowhere else --
student credentials are never persisted at all (see
anumati_integration/views.py, link_student_locker).
"""
from cryptography.fernet import Fernet
from django.conf import settings


def _fernet():
    return Fernet(settings.ANUMATI_CREDENTIAL_KEY.encode()
                   if isinstance(settings.ANUMATI_CREDENTIAL_KEY, str)
                   else settings.ANUMATI_CREDENTIAL_KEY)


def encrypt_secret(raw: str) -> bytes:
    return _fernet().encrypt(raw.encode())


def decrypt_secret(token: bytes) -> str:
    return _fernet().decrypt(bytes(token)).decode()
