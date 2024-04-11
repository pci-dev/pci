COAR Notify
===========

PCI contains a [COAR Notify](https://notify.coar-repositories.org/) implementation,
comprising a [Linked Data Notifications inbox](https://www.w3.org/TR/ldn/#receiver),
database storage of inbound and outbound notifications and IP-whitelist inbox acl.

The system handles incoming `coar-notify:EndorsementAction` requests
by creating a preprint recommendation workflow in PCI. Endorsement requests
are acknowledged with `coar-notify:TentativeAccept` or `coar-notify:Reject`
notifications to the sending party.

Upon completion of any PCI recommendation process, be it initiated via inbox
or pci user interface, the system sends `coar-notify:Review/EndorsementAction`
notifications to the inbox specified in the `rel="ldp#inbox"` Sign-Posting
header - if any - provided by the preprint-server on the document's URL.

The inbox at `/coar_notify/inbox` has IP-whitelist access-control. Allowed
client IPs can be configured via menu Admin > COAR whitelist - i.e. at
`/admin/edit_config/coar_whitelist` or directly in the pci config database.

To enable COAR Notify, `private/appconfig.ini` should contain the following section:

```ini
[coar_notify]
enabled = True
```


Checking it works
-----------------

To check that the coar notify sub-system works:
- use POST on `/coar_notify/inbox` to send inbound COAR notifications to PCI
- validate a PCI recommendation and check the preprint-server's inbox
  for received endorsement and review notifications
- use HEAD on `/coar_notify` or `/coar_notify/inbox` to see the Sign-Posting
  `"describedby"` header, pointing to `/coar_notify/system_description`

Both outbound notifications (to the remote preprint-server `inbox`)
and inbound notifications (posted to `coar_notify/inbox`)
are stored in table `t_coar_notifications` in the pci database.
Admins can see the list of notifications at `/coar_notify`.

The system provides self-description at `/coar_notify/system_description`
and annouces it via a `"describedby"` Sign-Posting header on `/coar_notify`.


Deployment
----------

The COAR sub-system requires the following extra python libs:
- requests
