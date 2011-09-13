from django import forms

from django_globals import globals

from notes.models import Note, Topic
from user_notes.models import ALLOWED_MODELS

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

    def get_noted_object(self):
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

    def clean_content_type(self):
        """
        Check if the content_type is in allowed models
        """
        content_type = self.cleaned_data['content_type']
        if '%s.%s' % (content_type.app_label, content_type.model) not in ALLOWED_MODELS:
            raise forms.ValidationError('It\'s not possible to add a note for this kind of object')
        return content_type

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
