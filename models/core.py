import typing
from django.db import models
from django.conf import settings
from tinymce.models import HTMLField
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.functional import cached_property
from django import forms
from django.core.handlers.wsgi import WSGIRequest


from sapp.models import SM, AbstractUser, ImageField, AbstractSettings, cls


class Settings(AbstractSettings):
    cols_css_class = "col-12"

    class Meta(SM.Meta):
        verbose_name = "SAPP Votes Settings"
        verbose_name_plural = "SAPP Votes Settings"
    
    open_voter_registration = models.BooleanField(default=False)


class Election(SM):
    icon = "fas fa-file-excel"
    list_field_names = ("id", "title")
    queryset_names = ("new_voters", "candidates", "centres")

    title = models.CharField(max_length=256)
    details = HTMLField(blank=True, null=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    votes_per_voter = models.PositiveSmallIntegerField(default=1)

    @cached_property
    def candidates(self):
        return Candidate.objects.filter(election=self)

    @cached_property
    def new_voters(self):
        return Voter.objects.filter(id=None)

    @cached_property
    def voters(self):
        return Voter.objects.filter(election=self)

    @cached_property
    def votes(self):
        return Vote.objects.filter(voter__election=self)

    @cached_property
    def centres(self):
        return Centre.objects.filter(voter__election=self)
    
    def get_state(self):
        result = {}
        total_votes = self.votes.count()
        for candidate in self.candidates:
            candidate_votes_count = self.votes.filter(candidate= candidate).count()
            candidate_votes_percentage = (candidate_votes_count * 100/total_votes) if total_votes else 0
            result[f"{candidate.pk}"] = {
                "votes_count": candidate_votes_count,
                "votes_percentage": round(candidate_votes_percentage, 2)
            }
        return result

    @cached_property
    def state(self):
        return self.get_state()
    
    def sync_votes(self):
        state = self.get_state()
        for k, v in state.items():
            Candidate.objects.filter(id=int(k)).update(
                votes_count=v["votes_count"],
                votes_percentage=v["votes_percentage"]
            )
        self.emit_realtime({
            "room": f"sapp_votes.election.state.{self.pk}",
            "event": "state",
            "data": state
        })
    
    def __str__(self):
        return f"{self.sm_str} {self.title}"


class Party(SM):
    icon = "fas fa-project-diagram"
    list_field_names = ("id", "name", "logo")

    name = models.CharField(max_length=256)
    about = HTMLField(blank=True, null=True)
    logo = ImageField(blank=True, null=True)
    relevance = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return self.name


class Candidate(SM):
    icon = "fas fa-address-book"
    list_field_names = ("id", "image", "full_name", "party", "votes_count", "votes_percentage")
    filter_field_names = ("party", "election")
    form_exclude_field_names = ("votes_count", "votes_percentage")

    class Meta(SM.Meta):
        unique_together = ("election", "id_number")

    user: models.ForeignKey[AbstractUser] = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    full_name = models.CharField(max_length=256)
    id_number = models.CharField(max_length=256)
    image = ImageField(blank=True, null=True, upload_to="sapp_votes_candidates")
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    party = models.ForeignKey(Party, on_delete=models.SET_NULL, blank=True, null=True)
    votes_count = models.IntegerField(default=0)
    votes_percentage = models.FloatField(default=0)
    about = HTMLField(blank=True, null=True)

    def __str__(self):
        return self.full_name


class Centre(SM):
    icon = "fas fa-person-booth"
    list_field_names = ("id", "name", "election")
    filter_field_names = ("election", )

    name = models.CharField(max_length=256)
    location = models.TextField(max_length=256, blank=True, null=True)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)

    @cached_property
    def voters(self):
        return Voter.objects.filter(election=self)

    def __str__(self):
        return self.name


class Voter(SM):
    icon = "fas fa-address-card"
    cols_css_class = cls.COL_LG6
    list_field_names = ("id", "image", "full_name", "id_number", "election")
    filter_field_names = ("election", "weight", "centre", "user")

    class Meta(SM.Meta):
        unique_together = ("election", "id_number")

    image = ImageField(blank=True, null=True, upload_to="sapp_votes_voters")
    user: models.ForeignKey[AbstractUser] = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    full_name = models.CharField(max_length=256, blank=True)
    id_number = models.CharField(max_length=256, blank=True)
    weight = models.PositiveSmallIntegerField(default=1)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    centre = models.ForeignKey(Centre, on_delete=models.SET_NULL, blank=True, null=True)

    def set_voter_details(self):
        if not self.full_name and self.user:
            self.full_name = self.user.get_full_name()
            self.id_number = self.user.str_id
    
    def clean_voter_details(self):
        if not (self.user or (self.full_name and self.id_number)):
            raise ValidationError("Either put user or both id number and full name")
    
    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        self.clean_voter_details()

    def save(self, *args, **kwargs):
        self.set_voter_details()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.str_id} {self.full_name}"


class Vote(SM):
    icon = "fas fa-allergies"
    list_field_names = ("id", "voter", "candidate")
    filter_field_names = ("candidate", )

    voter = models.ForeignKey(Voter, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    
    def clean_voter_votes(self):
        current_votes = Vote.objects.filter(voter=self.voter).count()
        if (current_votes + 1) > self.voter.election.votes_per_voter:
            raise ValidationError("Already voted!")
    
    def clean_voter_registration(self):
        if self.voter.election != self.candidate.election:
            raise ValidationError("Unregistered voter")
    
    def clean_vote_time(self):
        now = timezone.now()
        if (now > self.voter.election.end) or (now < self.voter.election.start):
            raise ValidationError("Election closed")
    
    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        self.clean_vote_time()
        self.clean_voter_registration()
        self.clean_voter_votes()

    def after_save(self, is_creation: bool):
        super().after_save(is_creation)
        self.voter.election.sync_votes()

    @classmethod
    def get_filters_form(cls, request: WSGIRequest, _fields: typing.Iterable = None):
        super_form = super().get_filters_form(request, _fields)
        class FormClass(super_form):
            candidate__election = forms.ModelChoiceField(Election.objects.all(), label="Election")
        return FormClass
