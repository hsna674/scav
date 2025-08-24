# Comprehensive Logging System

A complete logging and monitoring system has been implemented for the Scavenger Hunt application. This system tracks all user activities, flag submissions, challenge completions, and provides detailed analytics.

## Features

### 📊 Activity Dashboard

- **URL**: `/logging/dashboard/`
- **Access**: Staff members only
- Real-time overview of all site activities
- Filter by time period (last hour, 24 hours, week)
- Summary cards showing key metrics
- Most active users and class performance

### 🚩 Flag Submissions Tracking

- **URL**: `/logging/submissions/`
- **Access**: Staff members only
- Complete history of all flag submissions
- Filter by challenge, user, class, or correctness
- Shows submitted flags, success rates, and points awarded
- Pagination for large datasets

### 🎯 Challenge-Specific Analytics

- **URL**: `/logging/challenge/<id>/submissions/`
- **Access**: Staff members only
- Detailed submissions for specific challenges
- Success rates by class
- Challenge difficulty analysis
- Complete submission timeline

### 👤 User Activity Profiles

- **URL**: `/logging/user/<id>/activity/`
- **Access**: Staff members only
- Individual user activity history
- Personal statistics (submissions, success rate, points)
- Timeline of all user actions

### 🏆 Class Leaderboards

- **URL**: `/logging/leaderboard/`
- **Access**: Staff members only
- Class-by-class performance comparison
- Top contributors in each class
- Challenge difficulty rankings
- Customizable time periods

## What Gets Logged

### Automatic Activity Logging

1. **Login/Logout Events** - OAuth login/logout with timestamps and IP
2. **Page Views** - All main pages visited by authenticated users
3. **Flag Submissions** - Every flag attempt (correct/incorrect) with full details
4. **Challenge Completions** - When users/classes complete challenges
5. **Admin Actions** - Administrative activities in the system

### Detailed Information Stored

- **User Information**: Username, class year, IP address, user agent
- **Timestamps**: Precise timing of all activities
- **Flag Submissions**: Submitted text, correctness, points awarded
- **Success Metrics**: Success rates, completion statistics
- **Context Data**: Challenge details, categories, point values

## Admin Integration

### Enhanced Challenge Admin

- Direct links to view submissions for each challenge
- Bulk actions for releasing challenges
- Submission counts in list view

### Logging Models in Admin

All logging data is accessible through Django Admin:

- **Activity Logs** - Searchable by user, type, date
- **Flag Submissions** - Filter by challenge, correctness, class
- **Challenge Completions** - Track first completions and points
- **Page Views** - Monitor site usage patterns

### Quick Access

- **Navigation**: Staff dropdown menu → "Activity Dashboard"
- **Admin Interface**: Enhanced with direct submission links
- **Real-time Updates**: Dashboard auto-refreshes every 30 seconds

## Database Models

### ActivityLog

- Tracks all user activities with type categorization
- Stores IP address, user agent, and contextual details
- Indexed for fast querying by user, type, and timestamp

### FlagSubmission

- Complete record of every flag submission attempt
- Links to user and challenge with correctness tracking
- Points awarded and IP address logging

### ChallengeCompletion

- Records when users complete challenges
- Tracks class-level completions and first achievements
- Points earned and completion order

### PageView

- Monitors page access patterns
- Referer tracking and user agent analysis
- Anonymous and authenticated user tracking

## Security & Privacy

- **IP Address Logging**: For security monitoring and duplicate detection
- **Staff-Only Access**: All logging views require staff permissions
- **Read-Only Admin**: Logging entries cannot be modified through admin
- **Data Integrity**: Automatic logging prevents manual manipulation

## Performance Considerations

- **Database Indexing**: Optimized indexes for fast queries
- **Pagination**: Large datasets are paginated for performance
- **Efficient Queries**: Related data is prefetched to minimize database hits
- **Middleware Optimization**: Selective logging to avoid performance impact

## Usage Examples

### Finding Cheating Patterns

1. Go to Flag Submissions → Filter by challenge
2. Look for unusual submission patterns or timing
3. Check IP addresses for shared submissions
4. Review user activity timelines

### Monitoring Class Progress

1. Visit Class Leaderboard
2. Compare completion rates between classes
3. Identify struggling students or classes
4. Track point accumulation over time

### Challenge Difficulty Analysis

1. Check Challenge Submissions for specific challenges
2. Review success rates and attempt counts
3. Identify challenges that may need adjustment
4. Monitor first completion patterns

### User Support

1. Access User Activity for specific users
2. Review their submission history and errors
3. Check login patterns and engagement
4. Identify technical issues or confusion

## Migration and Setup

The logging system is automatically configured and ready to use:

1. **Database Tables**: Created via Django migrations
2. **Middleware**: Automatically logs activities
3. **Signal Handlers**: Track login/logout events
4. **Admin Integration**: Enhanced admin interfaces
5. **URL Configuration**: Logging routes configured

## Future Enhancements

Potential future improvements:

- **Export Functionality**: CSV/JSON data export
- **Advanced Analytics**: Graphs and charts
- **Real-time Notifications**: Alert for suspicious activity
- **API Endpoints**: Programmatic access to logging data
- **Automated Reports**: Scheduled email summaries
