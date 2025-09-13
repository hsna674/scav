from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from django.db import transaction

from ...logging.models import (
    ActivityLog,
    FlagSubmission,
    ChallengeCompletion,
)


class Command(BaseCommand):
    help = "Clean up old logging data with various options"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            help="Delete logs older than this many days (default: keep all)",
        )
        parser.add_argument(
            "--keep-recent",
            type=int,
            help="Keep only the most recent N records for each log type",
        )
        parser.add_argument(
            "--log-type",
            choices=["activity", "submissions", "completions", "all"],
            default="all",
            help="Which type of logs to clean up (default: all)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation prompt",
        )
        parser.add_argument(
            "--exclude-successful-submissions",
            action="store_true",
            help="When cleaning submissions, keep all correct flag submissions",
        )

    def handle(self, *args, **options):
        if not any([options["days"], options["keep_recent"]]):
            raise CommandError("You must specify either --days or --keep-recent option")

        if options["days"] and options["keep_recent"]:
            raise CommandError(
                "You cannot use both --days and --keep-recent options together"
            )

        # Calculate cutoff date if using --days
        cutoff_date = None
        if options["days"]:
            cutoff_date = timezone.now() - timedelta(days=options["days"])

        # Determine which models to clean
        models_to_clean = []
        if options["log_type"] in ["activity", "all"]:
            models_to_clean.append(("ActivityLog", ActivityLog))
        if options["log_type"] in ["submissions", "all"]:
            models_to_clean.append(("FlagSubmission", FlagSubmission))
        if options["log_type"] in ["completions", "all"]:
            models_to_clean.append(("ChallengeCompletion", ChallengeCompletion))
        # PageView model removed for performance - was creating database record for every page load

        # Calculate what would be deleted
        deletion_summary = {}
        total_to_delete = 0

        for model_name, model_class in models_to_clean:
            if options["days"]:
                queryset = model_class.objects.filter(timestamp__lt=cutoff_date)

                # Special handling for flag submissions
                if (
                    model_name == "FlagSubmission"
                    and options["exclude_successful_submissions"]
                ):
                    queryset = queryset.filter(is_correct=False)

            elif options["keep_recent"]:
                # Get IDs of records to keep (most recent N)
                keep_ids = list(
                    model_class.objects.order_by("-timestamp").values_list(
                        "id", flat=True
                    )[: options["keep_recent"]]
                )
                queryset = model_class.objects.exclude(id__in=keep_ids)

                # Special handling for flag submissions
                if (
                    model_name == "FlagSubmission"
                    and options["exclude_successful_submissions"]
                ):
                    # Keep all correct submissions regardless of age
                    queryset = queryset.filter(is_correct=False)

            count = queryset.count()
            deletion_summary[model_name] = count
            total_to_delete += count

        # Display summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("DELETION SUMMARY")
        self.stdout.write("=" * 50)

        if options["days"]:
            self.stdout.write(
                f"Deleting logs older than {options['days']} days ({cutoff_date.strftime('%Y-%m-%d %H:%M:%S')})"
            )
        elif options["keep_recent"]:
            self.stdout.write(
                f"Keeping only the most recent {options['keep_recent']} records per log type"
            )

        if options["exclude_successful_submissions"]:
            self.stdout.write(
                "Note: Keeping all successful flag submissions regardless of age"
            )

        self.stdout.write("")

        for model_name, count in deletion_summary.items():
            if count > 0:
                self.stdout.write(
                    self.style.WARNING(f"  {model_name}: {count:,} records")
                )
            else:
                self.stdout.write(f"  {model_name}: {count} records")

        self.stdout.write("")
        self.stdout.write(f"Total records to delete: {total_to_delete:,}")

        if total_to_delete == 0:
            self.stdout.write(self.style.SUCCESS("No records to delete."))
            return

        # Handle dry run
        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS("\nDRY RUN - No records were actually deleted.")
            )
            return

        # Confirmation prompt
        if not options["force"]:
            self.stdout.write("")
            confirm = input("Are you sure you want to delete these records? [y/N]: ")
            if confirm.lower() not in ["y", "yes"]:
                self.stdout.write("Operation cancelled.")
                return

        # Perform deletion
        self.stdout.write("\nDeleting records...")

        with transaction.atomic():
            deleted_counts = {}
            for model_name, model_class in models_to_clean:
                if deletion_summary[model_name] > 0:
                    if options["days"]:
                        queryset = model_class.objects.filter(timestamp__lt=cutoff_date)

                        # Special handling for flag submissions
                        if (
                            model_name == "FlagSubmission"
                            and options["exclude_successful_submissions"]
                        ):
                            queryset = queryset.filter(is_correct=False)

                    elif options["keep_recent"]:
                        # Get IDs of records to keep (most recent N)
                        keep_ids = list(
                            model_class.objects.order_by("-timestamp").values_list(
                                "id", flat=True
                            )[: options["keep_recent"]]
                        )
                        queryset = model_class.objects.exclude(id__in=keep_ids)

                        # Special handling for flag submissions
                        if (
                            model_name == "FlagSubmission"
                            and options["exclude_successful_submissions"]
                        ):
                            # Keep all correct submissions regardless of age
                            queryset = queryset.filter(is_correct=False)

                    deleted_count, _ = queryset.delete()
                    deleted_counts[model_name] = deleted_count
                    self.stdout.write(
                        f"  Deleted {deleted_count:,} {model_name} records"
                    )

        # Final summary
        total_deleted = sum(deleted_counts.values())
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Successfully deleted {total_deleted:,} total records.")
        )

        # Show remaining counts
        self.stdout.write("\nRemaining records:")
        for model_name, model_class in models_to_clean:
            remaining = model_class.objects.count()
            self.stdout.write(f"  {model_name}: {remaining:,} records")
