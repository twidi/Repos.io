# Repos.io / Copyright Stephane Angel / Creative Commons BY-NC-SA license

from django import forms
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.simplejson import dumps

from tagging.words import parse_tags

class TagAutocomplete(forms.widgets.Input):
    input_type = 'text'

    class Media:
        css = {
            'all': ('css/jquery.autocomplete.css',),
        }
        js = ('js/jquery.autocomplete.min.js',)

    def __init__(self, *args, **kwargs):
        self.available_tags = None
        super(TagAutocomplete, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        json_view = reverse('tagging_autocomplete')
        html = super(TagAutocomplete, self).render(name, value, attrs)

        params = dict(
            multiple = True,
            minChars = 0,
            delay = 100,
        )

        if self.available_tags is not None:
            params.update(dict(
                url = None,
                data = self.available_tags,
            ))

        js = u'<script type="text/javascript">jQuery().ready(function() { jQuery("#%s").autocomplete("%s", %s); });</script>' % (attrs['id'], json_view, dumps(params))
        return mark_safe("\n".join([html, js]))

    def set_available_tags(self, tags):
        """
        Set tags to look for in autocomplete mode
        """
        self.available_tags = tags


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

    def set_available_tags(self, tags):
        """
        Set tags to use in the autocomplete widget
        """
        if isinstance(self.widget, TagAutocomplete):
            self.widget.set_available_tags(tags)

    def clean(self, value):
        value = super(TagField, self).clean(value)
        try:
            return parse_tags(value.replace("\n", ", "))
        except ValueError:
            raise forms.ValidationError(_("Please see help text to know attended format"))

