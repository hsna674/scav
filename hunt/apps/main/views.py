from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone as tz
from datetime import timedelta
from django.conf import settings

from .models import Challenge, Class, Category

import logging

logger = logging.getLogger(__file__)

f = open("log.csv", "a+")


@login_required
def index(request):
    if request.user.is_participant() or request.user.is_staff:
        """
        Challenges fall into one of three statuses with respect to the user:
            - available (user can complete)
            - completed (completed by users's class)
            - locked (can only be completed by one class and has been completed)
        """
        data = sorted([(c.year, c.get_points()) for c in Class.objects.all()])
        challenges_completed_by_class = set(Class.objects.get(year=str(request.user.graduation_year)).challenges_completed.all())
        categories_dict = dict()
        for category in Category.objects.all():    
            challenges_dict = dict()
            for c in category.challenges.all():
                if c in challenges_completed_by_class:
                    challenges_dict[c.id] = [c, "completed"]
                elif c.locked:
                    challenges_dict[c.id] = [c, "locked"]
                else:
                    challenges_dict[c.id] = [c, "available"]
            categories_dict[category.id] = [category, challenges_dict]
        
        return render(request, "main/index.html", context={"categories": categories_dict,"data": data, "dark_mode": request.user.dark_mode})
    else:
        return redirect(reverse("main:overview"))

@login_required
def dark_mode(request):
    user = request.user
    user.dark_mode = not user.dark_mode
    user.save()
    return redirect(reverse("main:index"))

@login_required
def overview(request):
    data = sorted([(c.year, c.get_points()) for c in Class.objects.all()])
    return render(request, 'main/overview.html', context={'data': data})
    
@login_required
def challenge_detail(request, challenge_id):
    if request.user.is_participant() or request.user.is_staff:
        c = get_object_or_404(Challenge, pk=challenge_id)
        challenges_completed_by_class = set(Class.objects.get(year=str(request.user.graduation_year)).challenges_completed.all())
        if not c.unblocked:
            status = 'blocked'
        elif c in challenges_completed_by_class:
            status = 'completed'
        elif c.locked:
            status = 'locked'
        else:
            status = 'available'
        return render(request, 'main/detail.html', context={'status': status, 'challenge': c})
    else:
        return redirect(reverse("main:overview"))

def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

@login_required
def validate_flag(request):
    if is_ajax(request) and (request.user.is_participant() or request.user.is_staff):
        if tz.now() - request.user.last_submission_time < timedelta(seconds=settings.MIN_REQUEST_TIME):
            return JsonResponse({"result": "ratelimited"})
        request.user.last_submission_time = tz.now()
        request.user.save()
        
        challenge = get_object_or_404(Challenge, id=int(request.POST.get("challenge_id")))
        flag = request.POST.get("flag")
        
        f.write(f"{tz.now()},{request.user.username},{challenge.name},{flag}\n")
        f.flush()
        
        if flag.lower() == challenge.flag.lower():
            if not challenge.locked:
                request.user.challenges_done.add(challenge)
                if challenge.exclusive:
                    challenge.locked = True
                challenge.save()
                hoco_class = Class.objects.get(year=str(request.user.graduation_year))
                hoco_class.challenges_completed.add(challenge)
                hoco_class.save()
            response = {"result": "success"}
        else:
            response = {"result": "failure"}
        return JsonResponse(response)
    else:
        return PermissionDenied

@login_required
def support(request):
    return render(request, 'main/support.html')