Docker Container
================

The system can run as a docker container.

Note: the container does not run the mailing queue,
as this would require a valid mail server configuration.


Build the dev container
-----------------------

	docker build -t pci .


Run the dev container
---------------------

A./ one-shot, throw-away

	docker run --rm -it -p 8001:8001 pci

use ^C to quit.


B./ long-running, keep state

	docker run -d -p 8001:8001 pci

use `docker stop` and `docker start` to stop/restart.
use `docker rm` to dispose.


C./ one-shot, throw away, with local dev env mapping

	docker run --rm -it -p 8001:8001 -v `pwd`:/pci pci


Use the containerized PCI
-------------------------

	browse http://localhost:8001/pci

	docker exec -it <container id> sh
