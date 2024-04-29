routes_in = (
    ('/web2py$anything', '/admin$anything'),
    ('/pci$anything', '/pci$anything'),
    ('/$anything', '/pci/$anything'),
)
routes_out = [(x, y) for (y, x) in routes_in]

# direct tickets to /web2py instead of /admin
error_message_ticket = '''<html><body><h1>Internal error</h1>
     Ticket issued: <a href="/web2py/default/ticket/%(ticket)s"
     target="_blank">%(ticket)s</a></body></html>'''
