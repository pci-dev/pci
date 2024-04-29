Welcome to the `standalone API` site deployment.

Created with:
        git clone --depth=10 https://github.com/pci-dev/pci API
        cd API && make api

See targets `api` and `api.dismount` in Makefile.


This directory is a sparse checkout, shallow clone,
with the following make-generated symlinks:

- `controllers/default.py`
- `models/db_plug.py`


To update, use git pull.
