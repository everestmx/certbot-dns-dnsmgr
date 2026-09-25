"""
The `~certbot_dns_dnsmgr.dns_dnsmgr` plugin automates the process of
completing a ``dns-01`` challenge (`~acme.challenges.DNS01`) by creating, and
subsequently removing, TXT records using the DNSmanager API.


Named Arguments
---------------

========================================  =====================================
``--dns-dnsmgr-credentials``              DNSmanager API credentials_
                                          INI file. (Required unless the
                                          username, password and endpoint are
                                          given on the command line)
``--dns-dnsmgr-username``                 DNSmanager username.
``--dns-dnsmgr-password``                 DNSmanager password.
``--dns-dnsmgr-endpoint``                 DNSmanager API URL.
``--dns-dnsmgr-insecure``                 Do not verify the TLS certificate of
                                          the DNSmanager API.
``--dns-dnsmgr-propagation-seconds``      The number of seconds to wait for DNS
                                          to propagate before asking the ACME
                                          server to verify the DNS record.
                                          (Default: 10)
========================================  =====================================


Credentials
-----------

Use of this plugin requires a configuration file containing DNSmanager API
credentials (login and password of a user that can manage the domains).

.. code-block:: ini
   :name: credentials.ini
   :caption: Example credentials file:

   # DNSmanager API credentials used by Certbot
   dns_dnsmgr_username = admin
   dns_dnsmgr_password = mysecretpassword
   dns_dnsmgr_endpoint = https://dns.example.com:1500/dnsmgr
   # Uncomment if the panel uses a self-signed certificate
   # dns_dnsmgr_insecure = true

The path to this file can be provided interactively or using the
``--dns-dnsmgr-credentials`` command-line argument. Certbot records the path
to this file for use during renewal, but does not store the file's contents.

.. caution::
   You should protect these API credentials as you would a password. Users who
   can read this file can use these credentials to issue arbitrary API calls on
   your behalf. Users who can cause Certbot to run using these credentials can
   complete a ``dns-01`` challenge to acquire new certificates or revoke
   existing certificates for associated domains, even if those domains aren't
   being managed by this server.

Certbot will emit a warning if it detects that the credentials file can be
accessed by other users on your system. The warning reads "Unsafe permissions
on credentials configuration file", followed by the path to the credentials
file. This warning will be emitted each time Certbot uses the credentials file,
including for renewal, and cannot be silenced except by addressing the issue
(e.g., by using a command like ``chmod 600`` to restrict access to the file).

Examples
--------

.. code-block:: bash
   :caption: To acquire a certificate for ``example.com``

   certbot certonly \\
     --authenticator dns-dnsmgr \\
     --dns-dnsmgr-credentials ~/.secrets/certbot/dnsmgr.ini \\
     -d example.com

.. code-block:: bash
   :caption: To acquire a single certificate for both ``example.com`` and
             ``*.example.com``

   certbot certonly \\
     --authenticator dns-dnsmgr \\
     --dns-dnsmgr-credentials ~/.secrets/certbot/dnsmgr.ini \\
     -d example.com \\
     -d '*.example.com'

.. code-block:: bash
   :caption: To acquire a certificate for ``example.com``, waiting 240 seconds
             for DNS propagation

   certbot certonly \\
     --authenticator dns-dnsmgr \\
     --dns-dnsmgr-credentials ~/.secrets/certbot/dnsmgr.ini \\
     --dns-dnsmgr-propagation-seconds 240 \\
     -d example.com

"""
