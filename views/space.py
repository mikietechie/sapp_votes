from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.core.handlers.wsgi import WSGIRequest

from sapp_votes.models import Election

def index_view(request: WSGIRequest):
    return render(request, "sapp_votes/index.html", {
        "elections": Election.objects.all()
    })
