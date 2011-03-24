from django.utils.translation import ugettext as _
from django.http import HttpResponse
from django.template import loader, Context
from django.core.urlresolvers import reverse
from twistranet.core.views import BaseView, BaseIndividualView
from twistranet.twistapp.views.account_views import HomepageView
from twistranet.twistapp.forms.admin_forms import *
from twistranet.twistapp.models import Menu, MenuItem
try:
    #python >= 2.6
    import json
except:
    #python 2.5
    import simplejson as json

label_save = _('Save')
label_edit_menuitem = _('Edit menu entry')
label_delete_menuitem = _('Delete menu entry')
label_cancel = _('Cancel')

def get_item_template(id, label, title, description, parent_id, target_id,
                      link_url, view_path, type, position, level=0,
                      edit_form = None, state='inactive', status='edit'):

    t = loader.get_template('admin/menu_item_edit.part.html')
    c = Context ({'iid': id,
                 'ilabel': label,
                 'ititle': title,
                 'idescription': description,
                 'iparent_id': parent_id,
                 'itarget_id': target_id,
                 'ilink_url': link_url,
                 'iview_path': view_path,
                 'itype': type,
                 'iposition': position,
                 'level': level,
                 'label_edit_menuitem': label_edit_menuitem,
                 'label_save': label_save,
                 'label_delete_menuitem': label_delete_menuitem,
                 'label_cancel': label_cancel,
                 'edit_form' : edit_form,
                 'state': state,
                 'status': status,
                })
    return t.render(c)

def get_item_model(menu):
    """html model used by javascript
       to generate new item edit forms
       the prefix 'model-' is used by javascript to change values
    """
    return get_item_template('model-id', 'model-label', 'model-title', 'model-description', menu.id, 'model-target_id',
                             'model-link_url', 'model-view_path', 'model-type', 'model-position', level=0,
                              edit_form = None, state='active', status='add')

# used for menu_builder html calls
def get_html_menu_tree( menu, level=-1):
    html = ''
    level += 1
    position = 0
    for menuitem in menu.children:
        position += 1
        if menuitem.target:
            type = 'content'
            target_id = menuitem.target.object.id
            link_url = ''
            view_path = ''
            edit_form = MenuItemContentForm(instance=menuitem, initial={'target_id': target_id})
        elif menuitem.link_url:
            type = 'link'
            target_id = ''
            link_url = menuitem.link_url
            view_path = ''
            edit_form = MenuItemLinkForm(instance=menuitem)
        elif menuitem.view_path:
            type = 'view'
            target_id = ''
            link_url = ''
            view_path = menuitem.view_path
            edit_form = MenuItemViewForm(instance=menuitem)
        else:
            raise("Something's strange with this menuitem")
        html += get_item_template(menuitem.id, menuitem.label, menuitem.title, menuitem.description,
                                  menu.id, target_id, link_url, view_path, type, position, level, edit_form, 'inactive', 'edit')
        html += get_html_menu_tree(menuitem, level)
    return html

class MenuBuilder(BaseView):
    """
    A view used to build all menus
    """
    name = "menu_builder"
    template_variables = BaseView.template_variables + [
        "form",
        "menu",
        "topmenus",
        "mainmenu",
        "links_form",
        "referer_url",
        "item_model",
    ]
    template = 'admin/menu_builder_form.html'
    title = _("Menu Builder")
    
    def prepare_view(self, *args, **kw):
        self.account = self.auth
        self.actions = None
        self.topmenus = topmenus = Menu.objects.all()
        # start the menu builder for the first menu if exists
        if topmenus:
            self.menu = topmenus[0]
            self.mainmenu = '<ul id="menu-to-edit" class="menu ui-sortable">\n%s\n</ul>' %get_html_menu_tree(self.menu)
            self.item_model = get_item_model(self.menu)
        else:
            self.menu = None
            self.mainmenu = ''
            self.item_model = ''
        self.form = MenuBuilderForm()
        self.links_form = MenuItemLinkForm()
        referer_path = reverse(HomepageView.name)
        self.referer_url = self.request.build_absolute_uri(referer_path)


class MenuItemValidate(BaseView):
    """
    This view return inline validation in json format
    for menuitem inline forms
    """
    title = "Menu Item - Validation"
    name = "menuitem_validate"
    itemtype = ""
    form_class = MenuItemForm

    def prepare_view(self, itemtype):
        if itemtype == 'link':
            self.form_class = MenuItemLinkForm
        elif itemtype == 'content':
            self.form_class = MenuItemContentForm
        elif itemtype == 'view':
            self.form_class = MenuItemViewForm
        else:
            raise NotImplementedError("this menu item type doesn't exist")

        self.form = self.form_class(self.request.POST)

    def render_view(self,):
        if self.request.method == 'POST':
            data =  {'success' : self.form.is_valid(), 'errors' : self.form.errors}
            return HttpResponse( json.dumps(data),
                                 mimetype='text/plain')



###################
# For tests only  #
###################


class MenuEdit(BaseView):
    """
    A view used to edit a menu
    """
    name = "menu_edit"
    template_variables = BaseView.template_variables + [
        "form",
    ]
    template = 'admin/menu_edit.html'
    title = _("Menu Edit")
    model_lookup = Menu
    form_class = MenuForm
    
    
    def prepare_view(self, *args, **kw):
        super(MenuEdit, self).prepare_view(*args, **kw)
        self.account = self.auth
        self.actions = None

class MenuCreate(MenuEdit):
    """
    A view used to create a menu
    """
    name = "menu_create"
    title = _("Menu Create")

class MenuItemEdit(BaseIndividualView):
    """
    A view used to edit a menuitem
    """
    name = "menu_item_edit"
    model_lookup = MenuItem
    template = 'admin/menu_item_edit.html'
    title = _("MenuItem Edit")
    form_class = MenuItemForm
    
    
    def prepare_view(self, *args, **kw):
        super(MenuItemEdit, self).prepare_view(*args, **kw)
        self.account = self.auth
        self.actions = None

class MenuItemCreate(MenuItemEdit):
    """
    A view used to create a menuitem
    """
    name = "menu_item_create"
    title = _("MenuItem Create")