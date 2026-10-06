"""Platform credentials stored in the Windows Credential Manager.

The username is kept in settings.json; the password only lives in the Credential
Manager (entry "OTECImpronta"). A .env file with OTEC_USERNAME / OTEC_PASSWORD is
still honoured as a fallback for development.
"""
import logging
import os
from dataclasses import dataclass

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

from src.logging_setup import register_secret
from src.paths import APP_NAME, resource_dir

logger = logging.getLogger(__name__)

SERVICE = APP_NAME


@dataclass(frozen=True)
class Credentials:
    username: str
    password: str

    def __post_init__(self):
        register_secret(self.username)
        register_secret(self.password)

    def __repr__(self) -> str:  # never print the password by accident
        return f'Credentials(username={self.username!r}, password=***)'


def load(username: str) -> Credentials | None:
    """Return saved credentials for *username*, or the .env ones, or None."""
    if username:
        try:
            password = keyring.get_password(SERVICE, username)
        except KeyringError:
            logger.exception('Could not read the Credential Manager')
            password = None
        if password:
            return Credentials(username, password)
    return _load_from_env()


def save(credentials: Credentials) -> None:
    keyring.set_password(SERVICE, credentials.username, credentials.password)
    logger.info('Credentials saved in the Windows Credential Manager')


def delete(username: str) -> None:
    if not username:
        return
    try:
        keyring.delete_password(SERVICE, username)
        logger.info('Credentials removed from the Windows Credential Manager')
    except PasswordDeleteError:
        pass


def _load_from_env() -> Credentials | None:
    try:
        from dotenv import load_dotenv
        load_dotenv(resource_dir() / '.env')
    except ImportError:
        pass
    username, password = os.getenv('OTEC_USERNAME'), os.getenv('OTEC_PASSWORD')
    if username and password:
        return Credentials(username, password)
    return None
