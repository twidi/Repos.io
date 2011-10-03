from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _

from django_globals import globals
from notes.models import Note, Topic

from private.models import ALLOWED_MODELS
from tagging.words import edit_string_for_tags, parse_tags

class NoteBaseForm(forms.ModelForm):
    """
    Base forms with common stuff for NoteForm and NoteDeleteForm
    """
    class Meta:
        model = Note
        fields = ('object_id', 'content_type')

    def __init__(self, *args, **kwargs):
        """
        Simply hide the two fields
        """
        super(NoteBaseForm, self).__init__(*args, **kwargs)
        self.fields['object_id'].widget = forms.HiddenInput()
        self.fields['content_type'].widget = forms.HiddenInput()

    def get_related_object(self):
        """
        Return the noted object if valid, else None
        """
        if self.instance:
            return self.instance.content_object
        else:
            content_type = self.cleaned_data['content_type']
            if not content_type:
                return None
            return content_type.get_object_for_this_type(pk=self.cleaned_data['object_id'])

    def get_note_from_content_type(self):
        """
        Try to get an existing note from the content_type parameters
        """
        try:
            return Note.objects.get(
                content_type = self.cleaned_data['content_type'],
                object_id = self.cleaned_data['object_id'],
                author = globals.user
            )
        except:
            return None

    def clean_content_type(self):
        """
        Check if the content_type is in allowed models
        """
        content_type = self.cleaned_data['content_type']
        if '%s.%s' % (content_type.app_label, content_type.model) not in ALLOWED_MODELS:
            raise forms.ValidationError('It\'s not possible to manage notes for this kind of object')
        return content_type


class NoteForm(NoteBaseForm):
    """
    Form to add or edit *the* note to an object, by the currently logged user
    """
    class Meta(NoteBaseForm.Meta):
        fields = ('content', 'markup',) + NoteBaseForm.Meta.fields

    def __init__(self, *args, **kwargs):
        """
        If it's a form for a new note, a `noted_object` argument must be in kwargs
        """
        # get or create a note, to have content_type filled in the form
        if 'instance' not in 'kwargs' and 'noted_object' in kwargs:
            kwargs['instance'] = Note(content_object=kwargs.pop('noted_object'))

        super(NoteForm, self).__init__(*args, **kwargs)

        # change the help text for markup
        self.fields['markup'].help_text = self.fields['markup'].help_text\
            .replace('are using with this model', 'want to use')

    def save(self, commit=True):
        """
        Try to load an existing not for the current content_type and update it
        or create a new one
        """
        instance = super(NoteForm, self).save(commit=False)
        try:
            # try to load an existing note
            existing_instance = self.get_note_from_content_type()
            if not existing_instance:
                raise Note.DoesNotExist
            # use the loaded one and copy data from the temporary one
            current_instance = instance
            instance = existing_instance
            instance.content = current_instance.content
            instance.markup = current_instance.markup
        except Note.DoesNotExist:
            # continue creating the new note
            instance.author = globals.user
            # we don't use topics for now so we always use the same one
            topic, topic_created = Topic.objects.get_or_create(title='Private notes')
            instance.topic = topic

        # force notes to be private
        instance.public = False

        instance.save()
        self.instance = instance

        return instance


class NoteDeleteForm(NoteBaseForm):
    """
    Form used to delete a note of the currently logged user
    """
    class Meta(NoteBaseForm.Meta):
        fields = NoteBaseForm.Meta.fields

    def clean(self):
        """
        Check if the user can act on this note
        """
        cleaned_data = super(NoteBaseForm, self).clean()
        if not self.get_note_from_content_type():
            raise forms.ValidationError('This note is not yours or does\'t exist')

        return cleaned_data

    def save(self, commit=True):
        """
        Override the save to delete the object
        """
        self.get_note_from_content_type().delete()
        return None


class TagsBaseForm(forms.Form):
    """
    Base forms with common stuff for TagsForm and TagsDeleteForm
    """
    content_type = forms.IntegerField(widget = forms.HiddenInput())
    object_id = forms.IntegerField(widget = forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        """
        Save tagged_object
        """
        self.tagged_object = kwargs.pop('tagged_object', None)
        if self.tagged_object:
            if not kwargs.get('initial'):
                kwargs['initial'] = {}
            kwargs['initial'].update(dict(
                content_type = ContentType.objects.get_for_model(self.tagged_object).id,
                object_id = self.tagged_object.id,
            ))
        super(TagsBaseForm, self).__init__(*args, **kwargs)

    def get_related_object(self):
        """
        Return the tagged object if valid, else None
        """
        if self.tagged_object:
            return self.tagged_object
        else:
            content_type = self.cleaned_data['content_type']
            if not content_type:
                return None
            return content_type.get_object_for_this_type(pk=self.cleaned_data['object_id'])

    def clean_content_type(self):
        """
        Check if the content_type is in allowed models
        """
        content_type = ContentType.objects.get_for_id(self.cleaned_data['content_type'])
        if '%s.%s' % (content_type.app_label, content_type.model) not in ALLOWED_MODELS:
            raise forms.ValidationError('It\'s not possible to manage tags for this kind of object')
        return content_type

class TagField(forms.CharField):
    """
    Better TagField from taggit, that allows multi-line edit
    """
    widget = forms.Textarea

    def clean(self, value):
        value = super(TagField, self).clean(value)
        try:
            return parse_tags(value.replace("\n", ", "))
        except ValueError:
            raise forms.ValidationError(_("Please see help text to know attended format"))

class TagsForm(TagsBaseForm):
    """
    Form to add or edit tags for an object, by the currently logged user
    """
    tags = TagField(help_text='Enter one tag per line, or coma separated. A tag can be composed of many words if they are between double quotes.<br />Exemple : <blockquote>django, "python framework"<br/>my project: foobar<br/>web</blockquote>This will result in 4 tags : "<em>django</em>", "<em>python framework</em>", "<em>my project: foobar</em>" and "<em>web</em>"')

    def __init__(self, *args, **kwargs):
        """
        Set the defaults tags
        """
        tagged_object = kwargs.get('tagged_object')
        if tagged_object:
            if not kwargs.get('initial'):
                kwargs['initial'] = {}
            kwargs['initial']['tags'] = edit_string_for_tags(tagged_object.get_user_tags())
        super(TagsForm, self).__init__(*args, **kwargs)

    def save(self):
        """
        Get the tags from the form parsed by taggit, and save them to the tagged_object
        """
        tags = self.cleaned_data['tags']
        dict_tags = {}
        weight = len(tags)
        for tag in tags:
            dict_tags[tag] = weight
            weight -= 1

        owner = globals.user

        tagged_object = self.get_related_object()
        tagged_object.private_tags.set(dict_tags, owner=owner)


class TagsDeleteForm(TagsBaseForm):
    """
    Form used to delete a note of the currently logged user
    """

    def save(self):
        """
        Delete all tags for an object set by the currently logged user
        """
        owner = globals.user

        tagged_object = self.get_related_object()
        tagged_object.private_tags.clear(owner=owner)

