from django.shortcuts import render
from .tasks import notify_user, scan_ebay_items


# Create your views here.
def scan(request):
    scan_ebay_items()
