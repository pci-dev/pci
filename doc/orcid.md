Configure ORCID with PCI
=========================

1. Go to your ORCID account at https://orcid.org/.
2. Go to the **Developer tools** page.
3. Create an application with:
   - Application name: **Peer Community In**
   - Application URL: **https://peercommunityin.org/**
   - Application description: **PCI is a non-profit organization of researchers offering peer review, recommendation and publication of scientific articles in open access for free.**
4. In the **Redirection URI** section, add all the URLs of the different PCIs (corresponds to a whitelist of the sites that can use this ORCID APP).
5. In **private/appconfig.ini**, add:
```
[ORCID]
client_id = <Identifiant client>
client_secret = <Secret client>
```
  _**Identifiant client** et **Secret client** can be retrieved from the **Developer Tools** page on https://orcid.org/._


Testing ORCID on your local setup
---------------------------------

The ORCID whitelist requires fqdn and no port specs,
unfortunately the local PCI setup sits on localhost:8000.

To workaround the whitelist constraint and to allow local testing,
we have added a fake entry `localhost.local` to the whitelist.

To setup your local PCI to work with ORCID, do the following:

- add `127.0.0.1 localhost.local` to your `/etc/hosts`
- create a ssh portmap 80 => 8000 (or run PCI on port 80)
- access your local PCI as http://localhost.local/pci

(also, specify `client_id` and `client_secret` in `appconfig.ini`)

To create the ssh portmap:
```
sudo ssh $USER@localhost -i ~/.ssh/id_rsa -NL 80:localhost:8000
```
