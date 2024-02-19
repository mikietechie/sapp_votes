from django.db import models, transaction
from django.utils import timezone

from sapp.models import AbstractAction

from .core import Election


class SyncVotesAction(AbstractAction):
    election = models.ForeignKey(Election, on_delete=models.CASCADE)

    def set_name(self):
        self.name = self.name or f"Sync at {timezone.now()}"

    def process_action(self):
        super().process_action()
        self.election.sync_votes()


class CloneElectionAction(AbstractAction):
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    new_election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name="new_election")
    # clone_candidates = models.BooleanField(default=True)

    def clone_election(self):
        for centre in self.election.centres:
            centre.id = None
            new_centre = centre
            new_centre.save()
            for voter in centre.voters:
                voter.id = None
                voter.election = self.new_election
                voter.centre = new_centre
                try:
                    voter.save()
                except:
                    pass
        for voter in self.election.voters.filter(centre = None):
            voter.id = None
            voter.election = self.new_election
            try:
                voter.save()
            except:
                pass

    def process_action(self):
        super().process_action()
        with transaction.atomic():
            self.clone_election()
