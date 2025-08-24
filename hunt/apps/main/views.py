from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone as tz
from datetime import timedelta
from django.conf import settings

from .models import Challenge, Class, Category
from ..logging.utils import log_flag_submission, log_challenge_completion

import logging

logger = logging.getLogger(__file__)


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
        challenges_completed_by_class = set(
            Class.objects.get(
                year=str(request.user.graduation_year)
            ).challenges_completed.all()
        )
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

        return render(
            request,
            "main/index.html",
            context={
                "categories": categories_dict,
                "data": data,
                "dark_mode": request.user.dark_mode,
            },
        )
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
    return render(request, "main/overview.html", context={"data": data})


@login_required
def challenge_detail(request, challenge_id):
    if request.user.is_participant() or request.user.is_staff:
        c = get_object_or_404(Challenge, pk=challenge_id)
        challenges_completed_by_class = set(
            Class.objects.get(
                year=str(request.user.graduation_year)
            ).challenges_completed.all()
        )
        if not c.unblocked:
            status = "blocked"
        elif c in challenges_completed_by_class:
            status = "completed"
        elif c.locked:
            status = "locked"
        else:
            status = "available"
        return render(
            request, "main/detail.html", context={"status": status, "challenge": c}
        )
    else:
        return redirect(reverse("main:overview"))


def is_ajax(request):
    return request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


@login_required
def validate_flag(request):
    if is_ajax(request) and (request.user.is_participant() or request.user.is_staff):
        if tz.now() - request.user.last_submission_time < timedelta(
            seconds=settings.MIN_REQUEST_TIME
        ):
            return JsonResponse({"result": "ratelimited"})
        request.user.last_submission_time = tz.now()
        request.user.save()

        challenge = get_object_or_404(
            Challenge, id=int(request.POST.get("challenge_id"))
        )
        flag = request.POST.get("flag")

        is_correct = flag.lower() == challenge.flag.lower()
        points_awarded = 0

        # Log the flag submission
        log_flag_submission(
            user=request.user,
            challenge=challenge,
            submitted_flag=flag,
            is_correct=is_correct,
            points_awarded=0,  # Will be updated below if correct
            request=request,
        )

        if is_correct:
            if not challenge.locked:
                # Check if user already completed this challenge
                user_already_completed = request.user.challenges_done.filter(
                    id=challenge.id
                ).exists()

                if not user_already_completed:
                    points_awarded = challenge.points

                    # Add to user's completed challenges
                    request.user.challenges_done.add(challenge)

                    # Add to class completed challenges
                    hoco_class = Class.objects.get(
                        year=str(request.user.graduation_year)
                    )
                    class_already_completed = hoco_class.challenges_completed.filter(
                        id=challenge.id
                    ).exists()
                    first_for_class = not class_already_completed

                    hoco_class.challenges_completed.add(challenge)
                    hoco_class.save()

                    # If exclusive challenge, lock it
                    if challenge.exclusive:
                        challenge.locked = True
                    challenge.save()

                    # Log the completion
                    log_challenge_completion(
                        user=request.user,
                        challenge=challenge,
                        points_earned=points_awarded,
                        class_year=str(request.user.graduation_year),
                        first_for_class=first_for_class,
                        request=request,
                    )

                    # Update the flag submission with points awarded
                    from ..logging.models import FlagSubmission

                    FlagSubmission.objects.filter(
                        user=request.user,
                        challenge=challenge,
                        submitted_flag=flag,
                        is_correct=True,
                    ).update(points_awarded=points_awarded)

            response = {"result": "success", "points": points_awarded}
        else:
            response = {"result": "failure"}
        return JsonResponse(response)
    else:
        return PermissionDenied


@login_required
def support(request):
    return render(request, "main/support.html")
