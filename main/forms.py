import crispy_bootstrap5.bootstrap5
import crispy_forms.layout
from crispy_forms.helper import FormHelper
from django import forms
from . import models

class RegisterDeveloperForm(forms.Form):
    developer_id = forms.CharField(max_length=255, label="Apple Developer ID")
    email = forms.EmailField(max_length=255, label="Email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.add_layout(crispy_forms.layout.Layout(
            crispy_bootstrap5.bootstrap5.FloatingField('developer_id'),
            crispy_bootstrap5.bootstrap5.FloatingField('email'),
            crispy_forms.layout.Submit("submit", "Submit"),
        ))

class ProcessADPForm(forms.Form):
    adp_id = forms.UUIDField(label="Package ID")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_layout(crispy_forms.layout.Layout(
            crispy_bootstrap5.bootstrap5.FloatingField('adp_id'),
            crispy_forms.layout.Submit("submit", "Submit"),
        ))


class AppForm(forms.ModelForm):
    description = forms.CharField(label="Description", widget=forms.Textarea(attrs={"style": "height: 150px;"}), required=False)

    class Meta:
        model = models.App
        fields = ("developer_name", "name", "subtitle", "description", "icon", "tint_colour", "category")


class AppVersionForm(forms.ModelForm):
    date = forms.DateField(label="Date", widget=forms.DateInput(attrs={"type": "date"}))
    description = forms.CharField(label="Update description", widget=forms.Textarea(attrs={"style": "height: 250px;"}), required=False)

    class Meta:
        model = models.AppVersion
        fields = ("marketing_version", "date", "public", "description")


class SourceForm(forms.ModelForm):
    description = forms.CharField(label="Description", widget=forms.Textarea(attrs={"style": "height: 150px;"}), required=False)

    class Meta:
        model = models.Source
        fields = ("slug", "name", "subtitle", "description", "icon", "header", "website", "tint_colour")