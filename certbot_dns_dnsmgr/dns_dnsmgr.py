"""DNS Authenticator for DNSmanager."""
import logging
import warnings
import xml.etree.ElementTree as ET

import requests
import urllib3

from certbot import errors
from certbot.plugins import dns_common

logger = logging.getLogger(__name__)

TRUE_VALUES = ("1", "true", "yes", "on")

class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for DNSmanager

    This Authenticator uses the DNSmanager API to fulfill a dns-01 challenge.
    """

    description = "Obtain certificates using a DNS TXT record (if you are using DNSmanager for DNS)."
    ttl = 60

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add):  # pylint: disable=arguments-differ
        super().add_parser_arguments(add, default_propagation_seconds=10)
        add("credentials", help="DNSmanager API credentials INI file.")
        add("username", help="Username for DNSmanager API (can be used instead of INI file).")
        add("password", help="Password for DNSmanager API (can be used instead of INI file).")
        add("endpoint", help="URL of the DNSmanager API (can be used instead of INI file).")
        add(
            "insecure",
            action="store_true",
            default=False,
            help="Do not verify the TLS certificate of the DNSmanager API.",
        )

    def more_info(self):  # pylint: disable=missing-docstring
        return (
            "This plugin configures a DNS TXT record to respond to a dns-01 challenge using "
            "the DNSmanager API."
        )

    def _setup_credentials(self):
        if self.conf("username") and self.conf("password") and self.conf("endpoint"):
            self.credentials = None
        else:
            self.credentials = self._configure_credentials(
                "credentials",
                "DNSmanager credentials INI file",
                {
                    "endpoint": "URL of the DNSmanager API (e.g., https://example.com:1500/dnsmgr).",
                    "username": "Username for DNSmanager API.",
                    "password": "Password for DNSmanager API.",
                },
            )

    def _perform(self, domain, validation_name, validation):
        self._get_dnsmgr_client().add_txt_record(domain, validation_name, validation)

    def _cleanup(self, domain, validation_name, validation):
        self._get_dnsmgr_client().del_txt_record(domain, validation_name, validation)

    def _get_dnsmgr_client(self):
        insecure = bool(self.conf("insecure"))
        if self.credentials is None:
            endpoint = self.conf("endpoint")
            username = self.conf("username")
            password = self.conf("password")
        else:
            endpoint = self.credentials.conf("endpoint")
            username = self.credentials.conf("username")
            password = self.credentials.conf("password")
            insecure = insecure or (self.credentials.conf("insecure") or "").strip().lower() in TRUE_VALUES

        return _DNSmanagerClient(endpoint, username, password, self.ttl, verify=not insecure)


class _DNSmanagerClient:
    """
    Encapsulates all communication with the DNSmanager API.
    """

    def __init__(self, endpoint, username, password, ttl, verify=True):
        self.endpoint = endpoint.rstrip("/")
        if not self.endpoint.endswith("/dnsmgr"):
            self.endpoint += "/dnsmgr"
        self.authinfo = f"{username}:{password}"
        self.ttl = ttl
        self.verify = verify
        self.session = requests.Session()

    def _request(self, func, **params):
        """
        Call a DNSmanager API function and return the parsed XML document.
        """
        logger.debug("DNSmanager API request %s with params %s", func, params)
        data = {"authinfo": self.authinfo, "out": "xml", "func": func}
        data.update(params)

        try:
            with warnings.catch_warnings():
                if not self.verify:
                    warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
                resp = self.session.post(self.endpoint, data=data, verify=self.verify, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise errors.PluginError(f"Error communicating with the DNSmanager API: {e}")

        try:
            doc = ET.fromstring(resp.content)
        except ET.ParseError:
            raise errors.PluginError(f"DNSmanager API returned a non-XML response: {resp.text[:500]}")

        error = doc.find("error")
        if error is not None:
            message = error.findtext("msg") or error.get("type") or "unknown error"
            raise errors.PluginError(f"DNSmanager API error in {func}: {message}")

        return doc

    @staticmethod
    def _elems(doc):
        """
        Convert the <elem> children of a list response into dicts.
        """
        return [
            {child.tag: (child.text or "") for child in elem}
            for elem in doc.findall("elem")
        ]

    def _find_zone(self, domain):
        """
        Find the DNSmanager zone the domain belongs to (the longest matching one).
        """
        zones = {
            elem.get("name", "").rstrip(".").lower()
            for elem in self._elems(self._request("domain"))
        }
        for guess in dns_common.base_domain_name_guesses(domain):
            if guess.lower() in zones:
                logger.debug("Using DNSmanager zone %s for %s", guess, domain)
                return guess.lower()
        raise errors.PluginError(f"Unable to find DNSmanager zone for {domain}")

    def add_txt_record(self, domain, record_name, record_content):
        """
        Add a TXT record.
        """
        zone = self._find_zone(domain)
        fqdn = record_name.rstrip(".") + "."
        self._request(
            "domain.record.edit",
            plid=zone,
            name=fqdn,
            rtype="txt",
            value=record_content,
            ttl=self.ttl,
            sok="ok",
        )
        logger.info("Added TXT record %s to zone %s", fqdn, zone)

    def del_txt_record(self, domain, record_name, record_content):
        """
        Delete the TXT record with the given name and content.

        Failures are logged, not raised: cleanup must not break certificate issuance.
        """
        try:
            zone = self._find_zone(domain)
            fqdn = record_name.rstrip(".").lower()
            records = self._elems(self._request("domain.record", elid=zone))

            deleted = 0
            for record in records:
                if record.get("rtype", "").upper() != "TXT":
                    continue
                if record.get("value", "").strip('"') != record_content:
                    continue
                name = record.get("name", "").rstrip(".").lower()
                if name != fqdn and f"{name}.{zone}" != fqdn:
                    continue
                rkey = record.get("rkey")
                if not rkey:
                    logger.warning("TXT record %s has no rkey, cannot delete it", fqdn)
                    continue
                self._request("domain.record.delete", plid=zone, elid=rkey)
                logger.info("Deleted TXT record %s from zone %s", fqdn, zone)
                deleted += 1

            if deleted == 0:
                logger.debug("No TXT record %s with the given content found to delete", fqdn)
        except errors.PluginError as e:
            logger.warning("Unable to delete TXT record %s: %s", record_name, e)
