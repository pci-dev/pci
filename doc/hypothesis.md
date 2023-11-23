Configure Hypothes.is with PCI
==============================

1. Log in to PCI's Hypothes.is account at https://hypothes.is/.
2. Click on **settings -> Developer** and activate **developer mode**.
3. Retrieved the **API token**.
4. In **private/appconfig.ini**, add:
```
[hypothesis]
api_key = <API token>
```
