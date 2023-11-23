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
