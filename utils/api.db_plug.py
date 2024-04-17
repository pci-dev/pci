# db.py plug

class db:
    """
    db plug/mock for standalone api:

    - api/pci (cfg.description)
    - api/issn (cfg.issn)
    - module/utils.py (conf)
    """

    class cfg:
        issn = None
        description = "api"

    conf = {}
