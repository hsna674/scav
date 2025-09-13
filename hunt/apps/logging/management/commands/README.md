# Log Cleanup Management Command

The `cleanup_logs` management command provides a safe and flexible way to clean up old logging data.

## Usage

```bash
# Basic usage - show what would be deleted (dry run)
python manage.py cleanup_logs --days 30 --dry-run

# Delete logs older than 30 days
python manage.py cleanup_logs --days 30

# Keep only the most recent 1000 records of each type
python manage.py cleanup_logs --keep-recent 1000

# Delete only incorrect flag submissions older than 7 days
python manage.py cleanup_logs --days 7 --log-type submissions --exclude-successful-submissions

# Delete only page views (keep everything else)
python manage.py cleanup_logs --days 1 --log-type activity

# Clean up activity logs only, keeping recent 500
python manage.py cleanup_logs --keep-recent 500 --log-type activity
```

## Options

- `--days N`: Delete logs older than N days
- `--keep-recent N`: Keep only the most recent N records for each log type
- `--log-type TYPE`: Which logs to clean (`activity`, `submissions`, `completions`, `all`)
- `--dry-run`: Show what would be deleted without actually deleting
- `--force`: Skip confirmation prompt
- `--exclude-successful-submissions`: When cleaning submissions, keep all correct flag submissions

## Safety Features

1. **Dry run by default**: Use `--dry-run` to see what would be deleted
2. **Confirmation prompt**: Shows summary and asks for confirmation (unless `--force` is used)
3. **Transaction safety**: All deletions happen in a database transaction
4. **Detailed reporting**: Shows before/after counts for all log types
5. **Selective preservation**: Option to keep successful submissions even when cleaning

## Common Use Cases

### Daily Cleanup (Cron Job)

```bash
# Delete page views older than 7 days (they grow quickly)
python manage.py cleanup_logs --days 7 --log-type activity --force

# Keep only recent 10,000 activity logs (excluding page views)
python manage.py cleanup_logs --keep-recent 10000 --log-type activity --force
```

### Competition End Cleanup

```bash
# Keep only successful submissions and recent 1000 of each other log type
python manage.py cleanup_logs --keep-recent 1000 --exclude-successful-submissions
```

### Storage Emergency

```bash
# Aggressive cleanup - keep only recent 100 of each type
python manage.py cleanup_logs --keep-recent 100 --force
```

## Log Types

- **activity**: User login/logout, admin actions, flag submissions (page view logging removed for performance)
- **submissions**: Detailed flag submission records with submitted flags and points
- **completions**: Challenge completion records with points and class info
- **all**: All of the above (default)

Note: Page view logging was removed to improve performance - it was creating a database record for every page load.

## Performance Notes

- The command uses database indexes for efficient deletion
- Large deletions are performed in a single transaction
- Progress is shown for each log type being cleaned
- Counts are displayed before and after cleanup
