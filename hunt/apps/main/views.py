from ..logging.models import ChallengeCompletion

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone as tz
from datetime import timedelta
from django.conf import settings
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import resolve_url
from django.db.models import Q

from .models import Challenge, Class, Category
from .context_processors import is_hunt_active
from ..logging.utils import log_flag_submission, log_challenge_completion

import logging

logger = logging.getLogger(__name__)

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
        # OPTIMIZATION: Calculate all class points in a single query instead of N queries
        from django.db.models import Sum, Count

        class_points = {}
        try:
            # Get all class points in one query using aggregation
            class_points_data = ChallengeCompletion.objects.values(
                "class_year"
            ).annotate(total_points=Sum("points_earned"))
            for item in class_points_data:
                class_points[item["class_year"]] = item["total_points"] or 0
        except Exception:
            # Fallback to original method if ChallengeCompletion not available
            class_points = {c.year: c.get_points() for c in Class.objects.all()}

        # Ensure all classes are represented (even with 0 points)
        all_classes = Class.objects.all()
        for cls in all_classes:
            if cls.year not in class_points:
                class_points[cls.year] = 0

        data = sorted([(year, points) for year, points in class_points.items()])

        # Determine completed challenges for the user's class via ChallengeCompletion
        completed_ids = set(
            ChallengeCompletion.objects.filter(
                class_year=str(request.user.graduation_year)
            ).values_list("challenge_id", flat=True)
        )

        # OPTIMIZATION: Pre-calculate completion counts for decreasing challenges in a single query
        decreasing_challenge_completion_counts = {}
        try:
            decreasing_challenges = Challenge.objects.filter(
                challenge_type="decreasing"
            )
            if decreasing_challenges.exists():
                completion_counts = (
                    ChallengeCompletion.objects.filter(
                        challenge__in=decreasing_challenges,
                        first_completion_for_class=True,
                    )
                    .values("challenge_id")
                    .annotate(count=Count("class_year", distinct=True))
                )
                for item in completion_counts:
                    decreasing_challenge_completion_counts[item["challenge_id"]] = item[
                        "count"
                    ]
        except Exception:
            pass

        # OPTIMIZATION: Use prefetch_related to load all challenges efficiently
        categories_dict = dict()
        categories = Category.objects.prefetch_related("challenges").order_by(
            "order", "name"
        )

        for category in categories:
            challenges_dict = dict()
            # Filter challenges to only include released ones (unless user is staff)
            challenges_qs = category.challenges.order_by("order", "id")
            if not request.user.is_staff:
                # For non-staff users, filter to only show released challenges
                # This includes manually released (unblocked=True) or timed releases that have passed
                from django.utils import timezone

                now = timezone.now()
                challenges_qs = challenges_qs.filter(
                    Q(unblocked=True) | Q(timed_release=True, release_time__lte=now)
                )

            for c in challenges_qs:
                if c.id in completed_ids:
                    challenges_dict[c.id] = [c, "completed"]
                elif c.locked:
                    challenges_dict[c.id] = [c, "locked"]
                elif c.is_unlocking and not c.is_available_for_class(
                    request.user.graduation_year
                ):
                    # Calculate completion status for partial requirements
                    required_challenge_ids = set(
                        c.required_challenges.values_list("id", flat=True)
                    )
                    completed_challenge_ids = set(completed_ids)
                    completed_required_count = len(
                        required_challenge_ids.intersection(completed_challenge_ids)
                    )

                    # Determine how many challenges need to be completed
                    if (
                        c.required_challenges_count == 0
                        or c.required_challenges_count >= len(required_challenge_ids)
                    ):
                        needed_count = len(required_challenge_ids)
                    else:
                        needed_count = c.required_challenges_count

                    # Get all required challenges and their completion status
                    required_challenges_info = []
                    for req_challenge in c.required_challenges.all():
                        is_completed = req_challenge.id in completed_challenge_ids
                        required_challenges_info.append(
                            {"challenge": req_challenge, "completed": is_completed}
                        )

                    challenges_dict[c.id] = [
                        c,
                        "prerequisite_not_met",
                        {
                            "required_challenges": required_challenges_info,
                            "completed_count": completed_required_count,
                            "needed_count": needed_count,
                            "total_count": len(required_challenge_ids),
                        },
                    ]
                else:
                    if c.is_decreasing:
                        # OPTIMIZATION: Use pre-calculated completion count instead of querying database
                        classes_completed = decreasing_challenge_completion_counts.get(
                            c.id, 0
                        )
                        decay_factor = (100 - c.decay_percentage) / 100
                        current_points = c.points * (decay_factor**classes_completed)
                        current_points = max(1, round(current_points))
                        challenges_dict[c.id] = [c, "available", current_points]
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
                "user_graduation_year": str(request.user.graduation_year),
            },
        )
    else:
        # Fallback: if user is authenticated but not participant/staff, still show index (or redirect to login)
        return redirect(reverse("auth:login"))


@login_required
@require_POST
def dark_mode(request):
    user = request.user
    user.dark_mode = not user.dark_mode
    user.save(update_fields=["dark_mode"])

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        redirect_to = resolve_url(next_url)
    else:
        redirect_to = reverse("main:index")

    return redirect(redirect_to)


def is_ajax(request):
    return request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


@login_required
def validate_flag(request):
    if is_ajax(request) and (request.user.is_participant() or request.user.is_staff):
        # Check if hunt is active (allow staff to always submit)
        if not is_hunt_active() and not request.user.is_staff:
            return JsonResponse(
                {
                    "result": "hunt_inactive",
                    "message": "The hunt has ended and flag submissions are no longer accepted.",
                }
            )

        if tz.now() - request.user.last_submission_time < timedelta(
            seconds=settings.MIN_REQUEST_TIME
        ):
            return JsonResponse({"result": "ratelimited"})
        request.user.last_submission_time = tz.now()
        request.user.save()

        challenge = get_object_or_404(
            Challenge, id=int(request.POST.get("challenge_id"))
        )
        flag = request.POST.get("flag", "")

        # Check if challenge is released (for non-staff users)
        if not request.user.is_staff and not challenge.is_released():
            return JsonResponse(
                {
                    "result": "error",
                    "message": "This challenge is not yet available.",
                }
            )

        # Compare flags case-insensitively and ignore surrounding whitespace
        is_correct = flag.strip().lower() == challenge.flag.strip().lower()
        points_awarded = 0

        # Log the flag submission
        submission, activity_log = log_flag_submission(
            user=request.user,
            challenge=challenge,
            submitted_flag=flag,
            is_correct=is_correct,
            points_awarded=0,  # Will be updated below if correct
            request=request,
        )

        if is_correct:
            if not challenge.locked and (
                not challenge.is_unlocking
                or challenge.is_available_for_class(request.user.graduation_year)
            ):
                # Optimize: Check both user completion and class completion in single queries
                user_already_completed = request.user.challenges_done.filter(
                    id=challenge.id
                ).exists()

                if not user_already_completed:
                    # Get class object and check class completion in one go
                    try:
                        hoco_class = Class.objects.get(
                            year=str(request.user.graduation_year)
                        )
                    except Class.DoesNotExist:
                        logger.error(
                            f"Class not found for graduation year: {request.user.graduation_year}"
                        )
                        return JsonResponse(
                            {"result": "error", "message": "Invalid graduation year"}
                        )

                    # Check if this class already has a completion for this challenge
                    class_already_has_completion = ChallengeCompletion.objects.filter(
                        challenge=challenge,
                        class_year=str(request.user.graduation_year),
                    ).exists()
                    first_for_class = not class_already_has_completion

                    # Determine base points BEFORE mutating (for decreasing, based on current state)
                    if challenge.is_decreasing:
                        base_points = challenge.get_current_points()
                    else:
                        base_points = challenge.points

                    # Award points only for the first solver in a class
                    points_awarded = base_points if first_for_class else 0

                    # Update the flag submission with correct points
                    if submission:
                        submission.points_awarded = points_awarded
                        submission.save()
                    if activity_log and activity_log.details:
                        activity_log.details["points_awarded"] = points_awarded
                        activity_log.save()

                    # Persist user and class completion relations
                    request.user.challenges_done.add(challenge)
                    hoco_class.challenges_completed.add(challenge)

                    # Batch the saves - only save hoco_class, and save challenge only if needed
                    hoco_class.save()

                    # Lock exclusive challenges
                    if challenge.is_exclusive:
                        challenge.locked = True
                        challenge.save()  # Only save if we modified the challenge

                    # Log completion (also creates the ChallengeCompletion row)
                    completion = log_challenge_completion(
                        user=request.user,
                        challenge=challenge,
                        points_earned=points_awarded,
                        class_year=str(request.user.graduation_year),
                        first_for_class=first_for_class,
                        request=request,
                    )

                    # Fallback: ensure persistence if logger failed to create
                    if completion is None:
                        completion, _ = ChallengeCompletion.objects.get_or_create(
                            user=request.user,
                            challenge=challenge,
                            defaults={
                                "class_year": str(request.user.graduation_year),
                                "points_earned": points_awarded,
                                "first_completion_for_class": first_for_class,
                            },
                        )
                        # If row existed (shouldn't for first user+challenge), update fields just in case
                        if (
                            completion.class_year != str(request.user.graduation_year)
                            or completion.points_earned != points_awarded
                            or completion.first_completion_for_class != first_for_class
                        ):
                            completion.class_year = str(request.user.graduation_year)
                            completion.points_earned = points_awarded
                            completion.first_completion_for_class = first_for_class
                            completion.save()
                else:
                    # User already completed this challenge, no points
                    points_awarded = 0
                    if submission:
                        submission.points_awarded = points_awarded
                        submission.save()
                    if activity_log and activity_log.details:
                        activity_log.details["points_awarded"] = points_awarded
                        activity_log.save()
            else:
                # Challenge is locked or prerequisites not met, no points
                points_awarded = 0
                if submission:
                    submission.points_awarded = points_awarded
                    submission.save()
                if activity_log and activity_log.details:
                    activity_log.details["points_awarded"] = points_awarded
                    activity_log.save()

            response = {"result": "success", "points": points_awarded}

            # Only update decreasing challenges if this was a first completion that affects the counts
            if challenge.is_decreasing and points_awarded > 0:
                # Recompute updated display values for all decreasing challenges
                decreasing_challenges = {}
                from django.utils import timezone

                now = timezone.now()
                for ch in Challenge.objects.filter(challenge_type="decreasing").filter(
                    Q(unblocked=True) | Q(timed_release=True, release_time__lte=now)
                ):
                    decreasing_challenges[ch.id] = ch.get_current_points()
                response["decreasing_challenges_update"] = decreasing_challenges
        else:
            # Incorrect flag
            points_awarded = 0
            # submission.points_awarded is already 0, no need to update
            response = {"result": "failure"}
        return JsonResponse(response)
    else:
        return PermissionDenied


@login_required
def support(request):
    return render(
        request,
        "main/support.html",
        {
            "dark_mode": request.user.dark_mode,
        },
    )


def custom_404_view(request, exception):
    """Custom 404 view that renders our themed error page"""
    context = {}

    # Add dark mode context if user is authenticated
    if request.user.is_authenticated and hasattr(request.user, "dark_mode"):
        context["dark_mode"] = request.user.dark_mode
    else:
        context["dark_mode"] = False

    return render(request, "404.html", context, status=404)


def challenge_163624_view(request):
    """Challenge page that looks like 404 but has hidden riddle in console"""
    return render(request, "challenge_163624.html", status=404)


@require_POST
@login_required
def move_challenge_up(request):
    """Move a challenge up one position in the ordering"""
    if not request.user.is_staff:
        return JsonResponse({"success": False, "error": "Permission denied"})

    try:
        challenge_id = request.POST.get("challenge_id")
        category_id = request.POST.get("category_id")

        if not challenge_id or not category_id:
            return JsonResponse(
                {"success": False, "error": "Missing challenge_id or category_id"}
            )

        challenge = get_object_or_404(Challenge, id=challenge_id)
        category = get_object_or_404(Category, id=category_id)

        # Get all challenges in this category ordered by order, then id
        challenges_in_category = list(
            Challenge.objects.filter(category=category).order_by("order", "id")
        )

        # Find the current challenge's position
        try:
            current_index = challenges_in_category.index(challenge)
        except ValueError:
            return JsonResponse(
                {"success": False, "error": "Challenge not found in category"}
            )

        # Can't move up if it's already first
        if current_index == 0:
            return JsonResponse(
                {"success": False, "error": "Challenge is already at the top"}
            )

        # Get the challenge above it
        challenge_above = challenges_in_category[current_index - 1]

        # Swap their order values
        current_order = challenge.order
        above_order = challenge_above.order

        # If they have the same order, create a gap
        if current_order == above_order:
            # Set the current challenge to have a lower order than the one above
            challenge.order = above_order - 1
        else:
            # Swap the orders
            challenge.order = above_order
            challenge_above.order = current_order
            challenge_above.save()

        challenge.save()

        # Recalculate sequential ordering to clean up gaps/duplicates
        challenges_in_category_fresh = Challenge.objects.filter(
            category=category
        ).order_by("order", "id")
        for i, chall in enumerate(challenges_in_category_fresh, 1):
            if chall.order != i:
                chall.order = i
                chall.save()

        return JsonResponse({"success": True})

    except Exception as e:
        logger.error(f"Error moving challenge up: {str(e)}")
        return JsonResponse({"success": False, "error": "An error occurred"})


@require_POST
@login_required
def move_challenge_down(request):
    """Move a challenge down one position in the ordering"""
    if not request.user.is_staff:
        return JsonResponse({"success": False, "error": "Permission denied"})

    try:
        challenge_id = request.POST.get("challenge_id")
        category_id = request.POST.get("category_id")

        if not challenge_id or not category_id:
            return JsonResponse(
                {"success": False, "error": "Missing challenge_id or category_id"}
            )

        challenge = get_object_or_404(Challenge, id=challenge_id)
        category = get_object_or_404(Category, id=category_id)

        # Get all challenges in this category ordered by order, then id
        challenges_in_category = list(
            Challenge.objects.filter(category=category).order_by("order", "id")
        )

        # Find the current challenge's position
        try:
            current_index = challenges_in_category.index(challenge)
        except ValueError:
            return JsonResponse(
                {"success": False, "error": "Challenge not found in category"}
            )

        # Can't move down if it's already last
        if current_index == len(challenges_in_category) - 1:
            return JsonResponse(
                {"success": False, "error": "Challenge is already at the bottom"}
            )

        # Get the challenge below it
        challenge_below = challenges_in_category[current_index + 1]

        # Swap their order values
        current_order = challenge.order
        below_order = challenge_below.order

        # If they have the same order, create a gap
        if current_order == below_order:
            # Set the current challenge to have a higher order than the one below
            challenge.order = below_order + 1
        else:
            # Swap the orders
            challenge.order = below_order
            challenge_below.order = current_order
            challenge_below.save()

        challenge.save()

        # Recalculate sequential ordering to clean up gaps/duplicates
        challenges_in_category_fresh = Challenge.objects.filter(
            category=category
        ).order_by("order", "id")
        for i, chall in enumerate(challenges_in_category_fresh, 1):
            if chall.order != i:
                chall.order = i
                chall.save()

        return JsonResponse({"success": True})

    except Exception as e:
        logger.error(f"Error moving challenge down: {str(e)}")
        return JsonResponse({"success": False, "error": "An error occurred"})
