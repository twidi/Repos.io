from django import forms
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from tagging.words import parse_tags

class TagAutocomplete(forms.widgets.Input):
    input_type = 'text'

    class Media:
        css = {
            'all': ('css/jquery.autocomplete.css',),
        }
        js = ('js/jquery.autocomplete.min.js',)

    def render(self, name, value, attrs=None):
        json_view = reverse('tagging_autocomplete')
        html = super(TagAutocomplete, self).render(name, value, attrs)
        js = u'<script type="text/javascript">jQuery().ready(function() { jQuery("#%s").autocomplete("%s", { multiple: true }); });</script>' % (attrs['id'], json_view)
        return mark_safe("\n".join([html, js]))


class TagField(forms.CharField):
    """
    Better TagField from taggit, that allows multi-line edit
    """
    widget = TagAutocomplete
    _help_text =  'Enter tags separated by comas. A tag can be composed of many words if they are between double quotes.<br />Exemple : <blockquote>django, "python framework", "my project: foobar", web</blockquote>This will result in 4 tags : "<em>django</em>", "<em>python framework</em>", "<em>my project: foobar</em>" and "<em>web</em>"'

    def __init__(self, *args, **kwargs):
        if not kwargs.get('help_text'):
            kwargs['help_text'] = self._help_text
        super(TagField, self).__init__(*args, **kwargs)


    def clean(self, value):
        value = super(TagField, self).clean(value)
        try:
            return parse_tags(value.replace("\n", ", "))
        except ValueError:
            raise forms.ValidationError(_("Please see help text to know attended format"))

