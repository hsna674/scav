"""
Simple test to verify time correction works in database operations.
Run with: python manage.py shell < test_db_time.py
"""

from django.utils import timezone
from hunt.apps.logging.models import ActivityLog, ActivityType
from django.contrib.auth import get_user_model

User = get_user_model()

print("=== Database Time Correction Test ===")

# Show current times
current_corrected = timezone.now()
original_time = getattr(timezone, "_original_now", lambda: current_corrected)()
offset = current_corrected - original_time

print(f"Current corrected time: {current_corrected}")
print(f"Original system time: {original_time}")
print(f"Applied offset: {offset.total_seconds():.2f} seconds")

# Find a user for testing
test_user = User.objects.first()
if not test_user:
    print("No users found for testing")
else:
    print(f"Creating test log for user: {test_user.username}")

    # Create a new log entry
    log_entry = ActivityLog.objects.create(
        user=test_user,
        activity_type=ActivityType.ADMIN_ACTION,
        details={
            "action": "manual_time_test",
            "corrected_time": current_corrected.isoformat(),
            "original_time": original_time.isoformat(),
            "offset_seconds": offset.total_seconds(),
        },
    )

    print(f"Created log entry with timestamp: {log_entry.timestamp}")
    print(f"Entry ID: {log_entry.id}")

    # Verify it was saved with corrected time
    saved_entry = ActivityLog.objects.get(id=log_entry.id)
    print(f"Retrieved timestamp from DB: {saved_entry.timestamp}")

    time_diff = abs((saved_entry.timestamp - current_corrected).total_seconds())
    if time_diff < 2:  # Within 2 seconds is good
        print("✅ SUCCESS: Database timestamp matches corrected time!")
    else:
        print(f"❌ ISSUE: Database timestamp differs by {time_diff:.2f} seconds")

print("=== Test Complete ===")
