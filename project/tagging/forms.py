from django import forms
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from tagging.words import parse_tags

class TagAutocomplete(forms.widgets.Textarea):
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

    def clean(self, value):
        value = super(TagField, self).clean(value)
        try:
            return parse_tags(value.replace("\n", ", "))
        except ValueError:
            raise forms.ValidationError(_("Please see help text to know attended format"))

