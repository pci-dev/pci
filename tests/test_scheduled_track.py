from conftest import begin_import, end_import
from conftest import config_set_scheduled_track

config_set_scheduled_track(True)

begin_import()

from test_setup_article import *
from test_review_article import *
from test_submit_manuscript import *

end_import()
