from django import forms
from django.db import models
from django.forms import widgets
from django.forms import fields

from twistranet.twistranet.forms.base_forms import BaseForm
from twistranet.twistranet.lib import permissions
from twistranet.twistranet.forms.widgets import ResourceWidget, PermissionsWidget
from  twistranet.twistranet.lib.log import log

class CommunityForm(BaseForm):
    """
    Community edition.
    """
    class Meta:
        from twistranet.twistranet.models import Community
        model = Community
        fields = ('title', 'description', 'picture', 'permissions', )

        widgets = {
            "picture":              ResourceWidget(),   
            "permissions":          PermissionsWidget(),
        }

class AdministrationForm(CommunityForm):
    """
    Global community edition form.
    This holds the global-community specific configuration options.
    """
    class Meta:
        from twistranet.twistranet.models import GlobalCommunity
        model = GlobalCommunity
        fields = ("site_name", "baseline", "permissions", )
        
