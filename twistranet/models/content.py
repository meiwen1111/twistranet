from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import html, translation
import _basemanager
import twistable
from account import Account
from resource import Resource
from twistranet.lib import roles, permissions, languages, utils

class ContentManager(_basemanager.BaseManager):
    """
    This manager is used for secured content (via the secured()) method.
    Methods are useable if the _account attribute is set.
    
    For performance reasons, it's UP TO YOU to call the distinct() method.
    """
    def get_query_set(self):
        """
        Return a queryset of 100%-authorized objects.
        """
        # Check for anonymous query
        authenticated = self._getAuthenticatedAccount()
        base_query_set = super(ContentManager, self).get_query_set()
        if not authenticated or authenticated.__class__.__name__ == "AnonymousAccount":
            # If global community is restricted, don't return anything
            if not Account.objects.filter(object_type = "GlobalCommunity"):
                return base_query_set.none()       # An on-purpose invalid filter
            
            # Return anonymous objects if global community is listable to anonymous.
            # XXX TODO: Avoid the distinct method
            glob = Account.objects.get(object_type = "GlobalCommunity")
            return base_query_set.filter(
                _permissions__name = permissions.can_view,
                _permissions__role__in = roles.content_public.implied(),
                publisher___permissions__name = permissions.can_view,
                publisher___permissions__role__in = (roles.anonymous, ),
                )
        
        # System account: return all objects
        if authenticated.object_type == "SystemAccount":
            authenticated.systemaccount     # This is one more security check, will raise if DB is not properly set
            return base_query_set           # The base qset with no filter
        
        # XXX TODO: Avoid the distinct method
        return base_query_set.filter(self._getViewFilter(authenticated)).distinct()
        
            
    def getActivityFeed(self, account):
        """
        Return activity feed content for the given account
        It's content the account follows + content it produced + log messages he's the originator
        """
        return self.filter(
            Q(publisher = account) | Q(author = account) | Q(notification__who = account) | Q(notification__on_who = account)
            ).distinct()
        
    
    def _getViewFilter(self, account):
        """
        Get main security filter parameter. Send this to the filter() method of a queryset.
        This will behave normally, ie. will not shortcut SystemAccount stuff.
        """
        # Return all content objects I can reach
        my_network = account.network
        my_communities = account.communities
        communities_i_manage = () # XXX TODO
        # account.communities.filter(
        #             membership_manager__member = account,
        #             membership_manager__is_manager = True,
        #             )
        
        return (
            # Public stuff, ie. stuff I can view if I can view the publisher
            Q(
                _permissions__name = permissions.can_view,
                _permissions__role__in = roles.content_public.implied(),
                publisher___permissions__name = permissions.can_view,
                publisher___permissions__role__in = roles.authenticated.implied(),
            )
        ) | (
            # Stuff from the people in my network
            Q(
                publisher__in = my_network,
                _permissions__name = permissions.can_view,
                _permissions__role__in = roles.content_network.implied() + roles.content_public.implied(),
                publisher___permissions__name = permissions.can_view,
                publisher___permissions__role__in = roles.account_network.implied(),
            )
        ) | (
            # Stuff from the communities I'm in
            Q(
                publisher__in = my_communities,
                _permissions__name = permissions.can_view,
                _permissions__role__in = roles.content_community_member.implied() + roles.content_public.implied(),
                publisher___permissions__name = permissions.can_view,
                publisher___permissions__role__in = roles.community_member.implied(),
            )
        ) | (
            # Stuff from the communities I manage
            Q(
                publisher__in = communities_i_manage,
                _permissions__name = permissions.can_view,
                _permissions__role__in = roles.content_community_manager.implied() + roles.content_public.implied(),
                publisher___permissions__name = permissions.can_view,
                publisher___permissions__role__in = roles.community_manager.implied(),
            )
        ) | (
            # And, of course, what I wrote !
            Q(
                author = account,
            )
        )
    
    def getViewableBy(self, account):
        """
        Get content the given account can view.
        This will not return content that is not viewable by authenticated user (of course).
        """
        return self.get_query_set().filter(self._getViewFilter(account))
    
    @property
    def followed(self):
        """
        Followed content by currently auth user
        """
        account = self._getAuthenticatedAccount()
        return self.filter(self._getFollowFilter(account))
        
    def _getFollowFilter(self, account):
        """
        Return the filter parameter set to follow an account.
        """
        # Return stuff exclusively from people / communities I'm interested in
        my_relations = account.my_interest
        return Q(publisher__in = my_relations) | Q(publisher = account) | Q(author = account)
        
        
    def getFollowedBy(self, account):
        """
        Return a queryset of objects the account follows.
        You can specify another account for a wall display for example.
        If you want to see current user's followed stuff, use self.followed pty instead.
        """
        return self.filter(
                self._getViewFilter(account)
            ).filter(
                self._getFollowFilter(account)
            )
        

class _AbstractContent(twistable.Twistable):
    """
    We use this to enforce using our manager on subclasses.
    This way, we avoid enforcing you to re-declare objects = ContentManager() on each content class!
    
    See: http://docs.djangoproject.com/en/1.2/topics/db/managers/#custom-managers-and-model-inheritance
    """
    class Meta:
        abstract = True

    # Our security model
    objects = ContentManager()


class Content(_AbstractContent):
    """
    Abstract content representation class.
    
    If you want to create your own text-based content type, just add a text = models.TextField() line in your subclass.
    """
    # The publisher this content is published for
    publisher = models.ForeignKey(Account)                      # The account this content is published for.

    # Usual metadata
    created_at = models.DateTimeField(auto_now = True, db_index = True)
    author = models.ForeignKey(Account, related_name = "by")    # The original author account, 
                                                                # not necessarily the publisher (esp. for auto producers or communities)

    # Text representation of this content
    # Usually content is represented that way:
    # (pict) HEADLINE
    # Summary summary summary [Read more]
    # 
    # We store summary and headline in DB for performance and searchability reasons.
    # Heavy @-querying will be done at save time, not at display-time.
    # Both of them can contain links and minimal HTML formating.
    # Never let your users edit those fields directly, as they'll be flagged as html-safe!
    # If you want to change behaviour of those fields, override the preprocess_xxx methods.
    html_headline = models.CharField(max_length = 140)          # The computed headline (a-little-bit-more-than-a-title) for this content.
    html_summary = models.CharField(max_length = 1024)          # The computed summary for this content.
    text_headline = models.CharField(max_length = 140)          # The computed headline (a-little-bit-more-than-a-title) for this content.
    text_summary = models.CharField(max_length = 1024)          # The computed summary for this content.
    
    # Resources associated to this content
    resources = models.ManyToManyField(Resource, blank = True, null = True)
    
    # XXX TODO: Implement sources (ie. the client this 'tweet' is coming from)
    # source = "web"
    
    # I18N support
    language = models.CharField(
        max_length = 10,
        blank = True,
        choices = languages.available_languages,
        default = languages.available_languages[0][0],
        db_index = True,
        )
    # List of field name / generation method name. This is very useful when translating content.
    auto_values = (
        ("html_headline", "preprocess_html_headline", ),
        ("text_headline", "preprocess_text_headline", ),
        ("html_summary", "preprocess_html_summary", ),
        ("text_summary", "preprocess_text_summary", ),
    )
    # Not implemented yet
    # translation_of = models.ForeignKey(
    #     "Content",
    #     related_name = "translations",
    #     null = True,
    #     blank = True,
    #     )
    
    # Security models available for the user
    # XXX TODO: Use a foreign key instead with some clever checking, or, better create a new field type.
    permission_templates = permissions.content_templates
    permissions = models.CharField(
        max_length = 32,
        choices = permissions.content_templates.get_choices(), 
        default = permissions.content_templates.get_default(),
        db_index = True,
        )
        
    # View overriding support.
    # This will be saved into the Content object for performance reasons.
    # That way you don't have to dereference the underlying object until you want to see the whole page.
    # Overload the 'type_summary_view' in your subclasses if you want.
    # Same for detail_view. Set to 'None' if no detail view (so no links on summary views)
    type_summary_view = "content/summary.part.html"
    type_detail_view = "content/view.html"
    
    is_content = True   # XXX TODO: What is this for, BTW??
    
    def __unicode__(self):
        return "%s %d by %s" % (self.object_type, self.id, self.author)
    
    class Meta:
        app_label = 'twistranet'

    #                                                               #
    #                       Display management                      #
    # You can override this in your content types.                  #
    #                                                               #
    
    def preprocess_html_headline(self, text = None):
        """
        preprocess_html_headline => unicode string.
        
        Used to compute the headline displayed.
        You can have some logic to display a different headline according to the content's properties.
        Default is to display the 140 first characters (or so) of the raw text content.
        
        You can override this in your own content types if you want.
        """
        if text is None:
            text = getattr(self, "text", "")
        MAX_HEADLINE_LENGTH = 140 - 5
        text = html.escape(text)
        if len(text) >= MAX_HEADLINE_LENGTH:
            text = u"%s [...]" % text[:MAX_HEADLINE_LENGTH]
        text = utils.escape_links(text)
        return text
        
    def preprocess_text_headline(self, text = None):
        """
        Default is just tag-stripping
        """
        if text is None:
            text = self.preprocess_html_headline()
        return html.strip_tags(text)
        
    def preprocess_html_summary(self, text = None):
        """
        Return an HTML-safe summary.
        Default is to keep the 1024-or-so first characters and to keep basic HTML formating.
        PLUS don't set the summary if it's the same as the headline!
        """
        if text is None:
            text = getattr(self, "text", "")

        MAX_SUMMARY_LENGTH = 1024 - 10
        text = html.escape(text)
        if len(text) >= MAX_SUMMARY_LENGTH:
            text = u"%s [...]" % text[:MAX_SUMMARY_LENGTH]
        text = utils.escape_links(text)
        if text == self.preprocess_html_headline():
            text = ""

        return text
        
    def preprocess_text_summary(self, text = None):
        """
        Default is just tag-stripping
        """
        if text is None:
            text = self.preprocess_html_summary()
        return html.strip_tags(text)
        
    @property
    def summary_view(self):
        return self.model_class.type_summary_view
    
    @property
    def detail_view(self):
        return self.model_class.type_detail_view
        
    
    #                                                                   #
    #                       Security Management                         #
    # XXX TODO: Use a more generic approach? And some caching as well?  #
    #                                                                   #
    
    @property
    def can_list(self):
        """
        Same as can_view for content objects?
        XXX TODO: Clean that a little bit?
        """
        auth = Account.objects._getAuthenticatedAccount()
        return auth.has_permission(permissions.can_view, self)

    @property
    def can_view(self):
        auth = Account.objects._getAuthenticatedAccount()
        return auth.has_permission(permissions.can_view, self)

    @property
    def can_delete(self):
        auth = Account.objects._getAuthenticatedAccount()
        return auth.has_permission(permissions.can_delete, self)

    @property
    def can_edit(self):
        auth = Account.objects._getAuthenticatedAccount()
        return auth.has_permission(permissions.can_edit, self)
        
        
    # DO NOT OVERRIDE ANYTHING BELOW THIS LINE!

    #                                                               #
    #                   Content internal stuff                      #
    #                                                               #

    @property
    def model_class(self):
        """
        Return the subobject model class
        """
        return utils.get_model_class(self, Content, self.object_type)        

    @property
    def object(self):
        """
        Return the exact subclass this object belongs to.
        Use this to display it.
        """
        if self.id is None:
            raise RuntimeError("You can't get subclass until your object is saved in database.")
        return getattr(self, self.object_type.lower())
                
    def save(self, *args, **kw):
        """
        Populate special content information before saving it.
        See Content class documentation for more information on that.
        """
        import _permissionmapping
        
        # Confirm publishing rights
        authenticated = Content.objects._getAuthenticatedAccount()
        if not authenticated:
            raise PermissionDenied("Anonymous user can't publish anything.")
        if self.publisher_id is None:
            if not authenticated.can_publish:
                raise PermissionDenied("%s can't publish anything." % (authenticated, ))
        else:
            if not self.publisher.can_publish:
                raise PermissionDenied("%s can't publish on %s." % (authenticated, self.publisher, ))

        # Set author
        if self.author_id is None:
            self.author = authenticated
        else:
            if not self.id:
                raise PermissionDenied("You're not allowed to set the content author by yourself.")
        
        # Check if user has modification rights for existing content
        if self.id:
            if not self.can_edit:
                raise PermissionDenied("You're not allowed to edit this content.")
        
        # Check if we're saving a real object and not a generic Content one (which is prohibited).
        # This must be a programming error, then.
        if self.__class__.__name__ == Content.__name__:
            raise ValidationError("You cannot save a raw content object. Use a derived class instead.")
        self.object_type = self.__class__.__name__
                
        # Set publisher
        if self.publisher_id is None:
            self.publisher = self.author
            
        # Set headline and summary cached values
        self.html_headline = self.preprocess_html_headline()
        self.text_headline = self.preprocess_text_headline()
        self.html_summary = self.preprocess_html_summary()
        self.text_summary = self.preprocess_text_summary()
        
        # Actually save stuff
        ret = super(Content, self).save(*args, **kw)
        
        # Set/reset permissions. We do it last to be sure we've got an id.
        _permissionmapping._ContentPermissionMapping.objects._applyPermissionsTemplate(self)
        return ret


    def delete(self,):
        """
        Delete object after we've checked security
        """
        if self.id:
            if not self.can_delete:
                raise PermissionDenied("You're not allowed to delete this object.")
        return super(Content, self).delete()
