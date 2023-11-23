Configure Twitter with PCI
==========================

**For each Twitter account of each PCI:**

1. Go to the **Twitter developer** website : https://developer.twitter.com/en
2. Sign in with the Twitter account of the current PCI account.
   * If the App already exists:
     * **API Key and Secret** and **Access Token and Secret** are stored elsewhere, in a password database, else:
        1. Click on **Developer Portal** -> **Project & Apps** -> **\<App ID>**.
        2. You can't retrieve **API Key and Secret** and **Access Token and Secret** but you can regenerate them.  
        _**(Please note, you will then need to change the Twitter configuration in private/appconfig.ini of the current PCI)**_
    * If the App doesn't exist:
       1. Create the **Web App** and set app name, description and website URL.
       2. In **User authentication settings** page of the App, in section **App permissions**, activate **Read and write** App permissions.
       3. Generate **API Key and Secret** and **Access Token and Secret**.
3. In **private/appconfig.ini**, add:
```
[social_twitter]
general_api_key = <API Key of the general Twitter account>
general_api_secret = <API Secret of the general Twitter account>
general_access_token = <Access Token of the general Twitter account>
general_access_secret = <Access Secret of the general Twitter account>

specific_api_key = <API Key of the Twitter account of the current instance of PCI>
specific_api_secret = <API Secret of the Twitter account of the current instance of PCI>
specific_access_token = <Access Token of the Twitter account of the current instance of PCI>
specific_access_secret = <Access Secret of the Twitter account of the current instance of PCI>
```
**General Twitter account** is the common Twitter account for all PCI.  
**Specific Twitter account** is the Twitter account of the PCI instance to configure.  
_You can configure either one or the other, or both._

Configure Mastodon with PCI
===========================

**For each PCI:**

1. Go to the **Mastodon instance** website of the PCI instance. (ex: https://archaeo.social) and sign in.
2. Click on **preference** -> **Developement**:
    * If the App already exists:
       1. Click on PCI app name.
       2. You can retrieve **Access Token**.
    * If the App doesn't exist:
       1. Create the App and set app name, description and website URL.
       2. Activate **write:statuses** and **crypto**.
       3. Generate **Access Token**.
3. In **private/appconfig.ini**, add:
```
[social_mastodon]
general_access_token = <Access Token>
general_instance_url = <Instance URL (ex: https://archaeo.social)>

specific_access_token = <Access Token>
specific_instance_url = <Instance URL (ex: https://archaeo.social)>
```
**General Mastodon account** is the common Mastodon account for all PCI.  
**Specific Mastodon account** is the Mastodon account of the PCI instance to configure.  
_You can configure either one or the other, or both._
