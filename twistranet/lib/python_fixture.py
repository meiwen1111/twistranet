from django.db.models.query import QuerySet

class Fixture(object):
    """
    Used to import initial data
    """
    
    def __init__(self, model, logged_account = None, force_update = False, **kw):
        """
        logged_account is a slug
        """
        self.model = model
        self.force_update = force_update
        self.dict = kw
        self.logged_account = logged_account
        
    def apply(self,):
        """
        Create / update model. Use the 'slug' attribute to define unicity of the content.
        """
        from twistranet.models import Account
        slug = self.dict.get('slug', None)
        obj = None
        
        # Check if slug is given. Mandatory.
        if not self.dict.has_key('slug'):
            raise ValueError("You can't apply this fixture without a slug attribute. This is so to avoid duplicates.")
        
        # Set auth if necessary
        if self.logged_account:
            __account__ = Account.objects.get(slug = self.logged_account)
        
        # Create/get object
        if slug:
            obj_q = self.model.objects.filter(slug = slug)
            if obj_q.exists():
                if not self.force_update:
                    # Object already exists and we don't want to update. Keep it that way.
                    return
                obj = obj_q.get()
        if not obj:
            obj = self.model()
            
        # Set properties & save
        for k, v in self.dict.items():
            if isinstance(v, QuerySet):
                v = v.get()
            setattr(obj, k, v)
        obj.save()
        
        # Special treatment for translation stuff
        if obj.__class__.__name__ == "TranslationResource":
            obj.original_content._translation(language = obj.language).save()
        
        return obj
