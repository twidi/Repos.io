from django import forms
from django.conf import settings

from django_globals import globals

from notes.models import Note, Topic

ALLOWED_MODELS = settings.NOTES_ALLOWED_MODELS

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ('content', 'markup', 'object_id', 'content_type')

    def __init__(self, *args, **kwargs):
        """
        If it's a form for a new note, a `noted_object` argument must be in kwargs
        """
        # get or create a note, to have content_type filled in the form
        if 'instance' not in 'kwargs' and 'noted_object' in kwargs:
            kwargs['instance'] = Note(content_object=kwargs.pop('noted_object'))

        super(NoteForm, self).__init__(*args, **kwargs)

        # hide content type
        self.fields['object_id'].widget = forms.HiddenInput()
        self.fields['content_type'].widget = forms.HiddenInput()

        # change the help text for markup
        self.fields['markup'].help_text = self.fields['markup'].help_text\
            .replace('are using with this model', 'want to use')

    def clean_content_type(self):
        content_type = self.cleaned_data['content_type']
        if '%s.%s' % (content_type.app_label, content_type.model) not in ALLOWED_MODELS:
            raise forms.ValidationError('It\'s not possible to add a note for this kind of object')
        return content_type

    def save(self, commit=True):
        instance = super(NoteForm, self).save(commit=False)
        try:
            # try to load an existing note
            current_instance = instance
            instance = Note.objects.get(
                content_type = self.cleaned_data['content_type'],
                object_id = self.cleaned_data['object_id'],
                author = globals.user
            )
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

    def get_noted_object(self):
        if self.instance:
            return self.instance.content_object
        else:
            content_type = self.cleaned_data['content_type']
            if not content_type:
                return None
            return content_type.get_object_for_this_type(pk=self.cleaned_data['object_id'])
