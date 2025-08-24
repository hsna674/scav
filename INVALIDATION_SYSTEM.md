# Flag Submission & Challenge Completion Invalidation System

A comprehensive system for invalidating flag submissions and challenge completions when cheating is detected.

## Features

### 🚫 Admin Bulk Invalidation

- **Admin Interface**: Django admin interface for bulk actions
- **Flag Submissions**: Bulk invalidate multiple submissions at once
- **Challenge Completions**: Bulk invalidate multiple completions at once
- **Audit Logging**: All invalidation actions are logged for accountability

### 🎯 Individual Invalidation

- **Flag Submissions View**: One-click invalidation buttons on submissions
- **Challenge Submissions View**: Challenge-specific invalidation
- **User Activity View**: Invalidate specific user completions
- **Real-time Updates**: UI updates instantly after invalidation

### 📊 What Gets Invalidated

When a submission/completion is invalidated:

1. **Points Removal**: Points are removed from user and class totals
2. **Completion Removal**: Challenge completion record is deleted
3. **User Challenges**: Removed from user's completed challenges list
4. **Class Challenges**: Removed from class completed challenges (if last completion)
5. **Exclusive Unlock**: Exclusive challenges are unlocked if invalidated
6. **Flag Submission Update**: Corresponding flag submission points set to 0
7. **Audit Trail**: Action is logged with full details

## How to Use

### Via Admin Interface

1. **Navigate to Admin**: Go to Django Admin → Logging → Flag Submissions or Challenge Completions
2. **Select Submissions**: Check boxes for submissions/completions to invalidate
3. **Run Action**: Select "Invalidate selected submissions/completions" from Actions dropdown
4. **Confirm**: Click "Go" and confirm the action
5. **Review**: Check the success message for number of items invalidated

### Via Activity Dashboard

1. **Flag Submissions View** (`/logging/submissions/`):

   - Filter to find specific submissions
   - Click "Invalidate" button on correct submissions with points
   - Confirm the action in the popup dialog

2. **Challenge Submissions View** (`/logging/challenge/<id>/submissions/`):

   - View all submissions for a specific challenge
   - Click "Invalidate" on any correct submission to remove it
   - See real-time updates to the table

3. **User Activity View** (`/logging/user/<id>/activity/`):
   - Review a specific user's activity
   - Click "Invalidate" on any completion to remove it
   - Instantly see the completion marked as invalidated

## Impact on Points & Leaderboard

### Class Points Recalculation

- Class points are automatically recalculated when completions are invalidated
- Uses the `ChallengeCompletion` records for accurate point totals
- Leaderboard reflects changes immediately

### Decreasing Point Challenges

- When a completion is invalidated for a decreasing point challenge
- Subsequent completions maintain their original point values
- No automatic recalculation of point decay occurs

### Exclusive Challenges

- If an exclusive challenge completion is invalidated
- The challenge becomes available again for other classes
- `locked` status is automatically removed

## Security & Permissions

### Staff-Only Access

- All invalidation functions require staff permissions
- Uses `@staff_or_committee_required` decorator
- No student or participant access to invalidation features

### Audit Logging

Every invalidation action creates an audit log entry with:

- **Admin User**: Who performed the invalidation
- **Target User**: Whose submission/completion was invalidated
- **Challenge Details**: Which challenge was affected
- **Points Removed**: How many points were removed
- **Timestamp**: When the action occurred
- **IP Address**: Where the action originated from

### CSRF Protection

- All AJAX invalidation requests include CSRF tokens
- POST method required for all invalidation actions
- JSON responses prevent unauthorized access

## Examples

### Finding Suspicious Activity

1. **By IP Address**: Filter flag submissions by IP to find shared submissions
2. **By Timing**: Look for submissions at unusual times or rapid succession
3. **By Success Rate**: Users with unusually high success rates
4. **By Pattern**: Similar submission times across multiple users

### Common Invalidation Scenarios

1. **Shared Account**: Multiple users using the same account

   ```
   → Invalidate all completions for the shared period
   → Review IP addresses and timestamps
   ```

2. **Flag Sharing**: Users sharing flags with each other

   ```
   → Invalidate completions after the first legitimate solve
   → Check submission timing patterns
   ```

3. **Technical Cheating**: Users exploiting system vulnerabilities
   ```
   → Invalidate all affected submissions
   → Fix the underlying technical issue
   ```

## Database Schema

### ActivityLog Entry for Invalidation

```json
{
  "activity_type": "admin_action",
  "details": {
    "action": "invalidate_submission", // or "invalidate_completion"
    "invalidated_user": "username",
    "challenge_id": 123,
    "challenge_name": "Challenge Name",
    "points_removed": 50,
    "submission_id": 456, // for submission invalidation
    "completion_id": 789, // for completion invalidation
    "class_year": "2027" // for completion invalidation
  }
}
```

## Technical Implementation

### Invalidation Views

- `invalidate_submission(request, submission_id)`: Individual submission invalidation
- `invalidate_completion(request, completion_id)`: Individual completion invalidation

### Admin Actions

- `FlagSubmissionAdmin.invalidate_submissions()`: Bulk submission invalidation
- `ChallengeCompletionAdmin.invalidate_completions()`: Bulk completion invalidation

### JavaScript Functions

- `invalidateSubmission(submissionId)`: Frontend submission invalidation
- `invalidateCompletion(completionId)`: Frontend completion invalidation

## Best Practices

### Investigation First

1. **Gather Evidence**: Screenshot suspicious activity before invalidating
2. **Check Multiple Sources**: Cross-reference flag submissions, timestamps, and IP addresses
3. **Document Reasoning**: Keep notes on why specific submissions were invalidated

### Communication

1. **Notify Teams**: Inform organizing team of significant invalidations
2. **Student Communication**: Consider reaching out to affected students
3. **Policy Enforcement**: Apply invalidation consistently according to competition rules

### Post-Invalidation

1. **Monitor Impact**: Check that points and leaderboard updated correctly
2. **Watch for Patterns**: See if invalidated users change behavior
3. **Technical Fixes**: Address any system vulnerabilities that enabled cheating

## Troubleshooting

### Points Not Updating

- Check that `ChallengeCompletion` records were actually deleted
- Verify class M2M relationships were updated
- Look for any errors in the invalidation action logs

### UI Not Updating

- Ensure CSRF tokens are correctly included
- Check browser console for JavaScript errors
- Verify the user has staff permissions

### Exclusive Challenges Not Unlocking

- Confirm that `challenge.locked` was set to `False`
- Check that no other valid completions exist for the challenge
- Verify the challenge type is actually "exclusive"

## Migration & Setup

This system is automatically available in any environment with:

- Django admin access for staff users
- The logging app properly configured
- JavaScript enabled in staff browsers

No additional setup or migrations are required beyond the existing logging system.
