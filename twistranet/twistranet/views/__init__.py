# Import major views
from base_view import AsView
from account_views import *
from community_views import *
from content_views import *
from resource_views import *
from media_views import *

# Reference actions.
# Note that actions may be pushed into database one day.
BaseView.available_actions = [ ConfigurationEdit, PendingNetworkView, CommunityInvitations, MyCommunitiesView, CommunityCreate, ContentCreate, ]

UserAccountView.available_actions = super(UserAccountView, UserAccountView).available_actions + \
    [ AddToNetworkView, RemoveFromNetworkView, UserAccountEdit ]

CommunityView.available_actions = super(CommunityView, CommunityView).available_actions + \
    [ CommunityEdit, CommunityJoin, CommunityManageMembers, CommunityInvite, CommunityLeave, CommunityDelete, ]

ContentView.available_actions = super(ContentView, ContentView).available_actions + \
    [ ContentEdit, ContentDelete, ]
