COAR Notify
===========

PCI contains a demonstration [COAR Notify](https://notify.coar-repositories.org/) implementation,
comprising a [Linked Data Notifications inbox](https://www.w3.org/TR/ldn/#receiver)
and the ability to send notifications to an external pre-configured LDN inbox
in response to endorsement events.

To configure COAR Notify, your `private/appconfig.ini` should contain the following section, with appropriate URLs:

```ini
[coar_notify]
inbox_url = http://remote-service.invalid/inbox
base_url = http://this-service.invalid/pci/
```

If `coar_notify.inbox_url` is missing or empty, COAR Notify support — both the inbox and outward notifications — is
disabled.

We recommend against enabling the COAR sub-system in a real production system, because
it'll accept notifications from anywhere without authentication.


Checking it works
-----------------

To check that the coar notify sub-system works:
- use POST url `coar_notify/inbox` to send inbound COAR notifications to PCI
- validate a PCI recommendation and check the remote-service at `inbox_url` for received notifications

Both outbound notifications (to the remote service at `inbox_url`)
and inbound notifications (posted to `coar_notify/inbox`)
are stored in table `t_coar_notifications` in the pci database.


Deployment
----------

The COAR sub-system requires the following extra python libs:
- requests

The PCI `coar_notify/inbox` endpoint somehow requires the captcha to be turned off.  To disable
the captcha, comment-out the line `private` in section `[captcha]` in `appconfig.ini`.
