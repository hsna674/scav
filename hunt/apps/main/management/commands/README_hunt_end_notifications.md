# Hunt End Discord Notifications

This feature automatically sends a Discord notification with the final leaderboard when the hunt timer ends.

## How it works

1. **Automatic Detection**: The system checks if the hunt has ended based on the `HUNT_END_TIME` setting every time a main page is loaded.

2. **One-time Notification**: A lock file prevents duplicate notifications from being sent.

3. **Beautiful Formatting**: The Discord message includes:
   - Final leaderboard with rankings (🥇🥈🥉)
   - Points for each class
   - Winner announcement
   - Hunt year and timestamp

## Configuration

Make sure your Discord settings are configured in `hunt/settings/secret.py`:

```python
# Discord settings (same as for first blood notifications)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
DISCORD_NOTIFICATIONS_ENABLED = True
```

## Manual Management

You can manage the hunt end notifications using the management command:

### Check and send notification

```bash
python manage.py check_hunt_end
```

### Force send notification (even if hunt is still active)

```bash
python manage.py check_hunt_end --force
```

### Reset the lock file (allows sending notification again)

```bash
python manage.py check_hunt_end --reset
```

## Scheduled Checking (Optional)

For more reliable notification timing, you can set up a cron job to check every minute:

```bash
# Add to crontab (crontab -e)
* * * * * cd /path/to/your/project && python manage.py check_hunt_end
```

## Lock File Location

The notification lock file is stored at `/tmp/hunt_end_notification_sent.lock` to prevent duplicate notifications.

## Troubleshooting

- **Notification not sent**: Check that `DISCORD_NOTIFICATIONS_ENABLED = True` and `DISCORD_WEBHOOK_URL` is set
- **Duplicate notifications**: The lock file should prevent this, but you can reset it with `--reset`
- **Manual testing**: Use `--force` to test the notification before the hunt actually ends
- **Check logs**: Look for Discord-related error messages in the Django logs

## Integration with First Blood

This feature reuses the same Discord configuration as the existing first blood notifications, so no additional setup is required if first blood notifications are already working.
