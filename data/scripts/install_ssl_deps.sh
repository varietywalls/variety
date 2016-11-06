#!/bin/bash

# The Python/OpenSSL/requests combination used by Variety to connect to https sites
# requires some dependencies to be installed, or some SSL connections will not succeed.
# Read more about the issues here:
# http://stackoverflow.com/questions/18578439/using-requests-with-tls-doesnt-give-sni-support/18579484

echo "Installing
Read on the URL below for more info, or google 'Python SNI requests':
http://stackoverflow.com/questions/18578439/using-requests-with-tls-doesnt-give-sni-support/18579484" > /var/log/variety_install_ssl_deps.log

which pip || ( curl https://bootstrap.pypa.io/get-pip.py | python - )
pip install pyOpenSSL ndg-httpsclient pyasn1 2>&1 >> /var/log/variety_install_ssl_deps.log
