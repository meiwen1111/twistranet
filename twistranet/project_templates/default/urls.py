from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Dynamic twistranet urls
    ("^",                                       include("twistranet.twistapp.urls")),

    # Additional inclusions for extensions, etc
    (r'^search/',                               include('twistranet.search.urls')),
    (r'^static/',                               include('twistranet.twistorage.urls')),
    (r'^download/',                             include('twistranet.twistorage.urls')),

    # 3rd party modules
    (r'^admin/',                                include(admin.site.urls)),
    (r'^tinymce/',                              include('tinymce.urls')),
)
