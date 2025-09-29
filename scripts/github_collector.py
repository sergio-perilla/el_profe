#!/usr/bin/env python3
"""
GitHub Activity Collector for Garmin Surf Training Data Pipeline

Collects daily GitHub activity metrics including commits, repositories, 
work patterns, and coding focus for correlation with physical training data.
"""

import requests
import json
import os
import logging
from datetime import datetime, date, timedelta
from collections import defaultdict, Counter
import time

logger = logging.getLogger(__name__)

class GitHubActivityCollector:
    def __init__(self, username, token):
        self.username = username
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.last_sync_file = "data/metadata/github_last_sync.json"
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def load_last_sync_state(self):
        """Load the last sync state from file"""
        try:
            if os.path.exists(self.last_sync_file):
                with open(self.last_sync_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load GitHub sync state: {e}")
        
        # Default state for first run
        return {
            "last_successful_sync": None,
            "repos_discovered": 0,
            "repos_last_sync": {}
        }
    
    def save_sync_state(self, state):
        """Save the sync state to file"""
        try:
            os.makedirs(os.path.dirname(self.last_sync_file), exist_ok=True)
            with open(self.last_sync_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save GitHub sync state: {e}")
    
    def get_rate_limit_status(self):
        """Check current rate limit status"""
        try:
            response = self.session.get('https://api.github.com/rate_limit')
            if response.status_code == 200:
                data = response.json()
                core_limit = data['resources']['core']
                return {
                    'remaining': core_limit['remaining'],
                    'limit': core_limit['limit'],
                    'reset_time': datetime.fromtimestamp(core_limit['reset'])
                }
        except Exception as e:
            logger.warning(f"Could not check rate limit: {e}")
        return {'remaining': 0, 'limit': 5000, 'reset_time': datetime.now() + timedelta(hours=1)}
    
    def wait_for_rate_limit(self):
        """Wait if we're approaching rate limits"""
        rate_limit = self.get_rate_limit_status()
        if rate_limit['remaining'] < 100:  # Conservative threshold
            wait_time = (rate_limit['reset_time'] - datetime.now()).total_seconds() + 60
            if wait_time > 0:
                logger.info(f"Rate limit low ({rate_limit['remaining']}), waiting {wait_time/60:.1f} minutes")
                time.sleep(min(wait_time, 3600))  # Max 1 hour wait
    
    def get_all_repositories(self):
        """Get all user repositories (public and private)"""
        repos = []
        page = 1
        per_page = 100
        
        while True:
            self.wait_for_rate_limit()
            
            try:
                url = f'https://api.github.com/user/repos'
                params = {
                    'per_page': per_page,
                    'page': page,
                    'sort': 'updated',
                    'affiliation': 'owner'  # Only repos owned by user
                }
                
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                page_repos = response.json()
                if not page_repos:
                    break
                
                repos.extend(page_repos)
                page += 1
                
                logger.debug(f"Retrieved page {page-1}, total repos so far: {len(repos)}")
                
            except Exception as e:
                logger.error(f"Failed to get repositories page {page}: {e}")
                break
        
        logger.info(f"Discovered {len(repos)} repositories for {self.username}")
        return repos
    
    def get_commits_for_repo(self, repo_name, since_date=None):
        """Get commits for a specific repository since given date"""
        commits = []
        
        try:
            self.wait_for_rate_limit()
            
            url = f'https://api.github.com/repos/{self.username}/{repo_name}/commits'
            params = {'author': self.username}
            
            if since_date:
                params['since'] = since_date.isoformat()
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            commits_data = response.json()
            
            for commit in commits_data:
                try:
                    commit_date = commit['commit']['author']['date']
                    commit_datetime = datetime.fromisoformat(commit_date.replace('Z', '+00:00'))
                    
                    commits.append({
                        'repo': repo_name,
                        'sha': commit['sha'][:8],
                        'message': commit['commit']['message'].split('\n')[0][:100],  # First line, truncated
                        'date': commit_datetime.date().isoformat(),
                        'time': commit_datetime.time().strftime('%H:%M'),
                        'datetime': commit_datetime,
                        'additions': 0,  # Will be filled by detailed API call if needed
                        'deletions': 0   # Will be filled by detailed API call if needed
                    })
                except Exception as e:
                    logger.warning(f"Error processing commit {commit.get('sha', 'unknown')}: {e}")
                    continue
            
            logger.debug(f"Retrieved {len(commits)} commits from {repo_name}")
            
        except Exception as e:
            logger.warning(f"Failed to get commits for {repo_name}: {e}")
        
        return commits
    
    def get_commit_stats(self, repo_name, commit_sha):
        """Get detailed stats (additions/deletions) for a specific commit"""
        try:
            self.wait_for_rate_limit()
            
            url = f'https://api.github.com/repos/{self.username}/{repo_name}/commits/{commit_sha}'
            response = self.session.get(url)
            response.raise_for_status()
            
            commit_data = response.json()
            stats = commit_data.get('stats', {})
            
            return {
                'additions': stats.get('additions', 0),
                'deletions': stats.get('deletions', 0),
                'total_changes': stats.get('total', 0)
            }
            
        except Exception as e:
            logger.warning(f"Failed to get stats for commit {commit_sha}: {e}")
            return {'additions': 0, 'deletions': 0, 'total_changes': 0}
    
    def detect_language_from_repo(self, repo_data):
        """Detect primary language from repository data"""
        return repo_data.get('language', 'unknown').lower() if repo_data.get('language') else 'unknown'
    
    def categorize_repo(self, repo_name, repo_data):
        """Categorize repository as work, personal, or other"""
        name = repo_name.lower()
        description = (repo_data.get('description') or '').lower()
        
        # Work indicators
        work_keywords = ['api', 'service', 'backend', 'frontend', 'client', 'server', 'prod', 'staging']
        # Personal indicators  
        personal_keywords = ['personal', 'blog', 'portfolio', 'learning', 'tutorial', 'experiment']
        # Training/analysis indicators
        training_keywords = ['training', 'analysis', 'data', 'pipeline', 'surf', 'garmin']
        
        text_to_check = f"{name} {description}"
        
        if any(keyword in text_to_check for keyword in training_keywords):
            return 'training'
        elif any(keyword in text_to_check for keyword in work_keywords):
            return 'work'
        elif any(keyword in text_to_check for keyword in personal_keywords):
            return 'personal'
        else:
            return 'other'
    
    def analyze_daily_activity(self, all_commits, repos_data):
        """Process all commits into daily activity metrics"""
        daily_activity = defaultdict(lambda: {
            'commits_count': 0,
            'repos_active': set(),
            'lines_added': 0,
            'lines_deleted': 0,
            'commit_times': [],
            'languages_used': set(),
            'repo_categories': set(),
            'commit_messages': [],
            'repos_list': []
        })
        
        # Create repo lookup for metadata
        repo_lookup = {repo['name']: repo for repo in repos_data}
        
        # Process each commit
        for commit in all_commits:
            commit_date = commit['date']
            repo_name = commit['repo']
            
            # Get repo metadata
            repo_data = repo_lookup.get(repo_name, {})
            language = self.detect_language_from_repo(repo_data)
            category = self.categorize_repo(repo_name, repo_data)
            
            # Aggregate daily data
            day_data = daily_activity[commit_date]
            day_data['commits_count'] += 1
            day_data['repos_active'].add(repo_name)
            day_data['commit_times'].append(commit['time'])
            day_data['languages_used'].add(language)
            day_data['repo_categories'].add(category)
            day_data['commit_messages'].append(commit['message'])
            day_data['repos_list'].append(repo_name)
            
            # Add line changes (if available)
            day_data['lines_added'] += commit['additions']
            day_data['lines_deleted'] += commit['deletions']
        
        # Convert to final format
        processed_data = []
        
        for date_str, data in daily_activity.items():
            commit_times = [datetime.strptime(t, '%H:%M').time() for t in data['commit_times']]
            
            # Calculate derived metrics
            first_commit = min(commit_times) if commit_times else None
            last_commit = max(commit_times) if commit_times else None
            
            work_span_hours = 0
            if first_commit and last_commit and len(commit_times) > 1:
                first_dt = datetime.combine(date.today(), first_commit)
                last_dt = datetime.combine(date.today(), last_commit)
                work_span_hours = (last_dt - first_dt).total_seconds() / 3600
            
            # Focus score (inverse of repo count - fewer repos = higher focus)
            repos_count = len(data['repos_active'])
            focus_score = round(1.0 / repos_count if repos_count > 0 else 0, 3)
            
            # Commit frequency (commits per hour during active time)
            commit_frequency = 0
            if work_span_hours > 0:
                commit_frequency = round(data['commits_count'] / work_span_hours, 2)
            elif data['commits_count'] > 0:
                commit_frequency = data['commits_count']  # Single commit burst
            
            # Late night commits (after 10 PM)
            late_night_commits = sum(1 for t in commit_times if t.hour >= 22)
            
            # Weekend indicator
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            is_weekend = 1 if date_obj.weekday() >= 5 else 0
            
            # Primary language and category
            primary_language = Counter(data['languages_used']).most_common(1)[0][0] if data['languages_used'] else 'none'
            primary_category = Counter(data['repo_categories']).most_common(1)[0][0] if data['repo_categories'] else 'none'
            
            processed_data.append({
                'date': date_str,
                'commits_count': data['commits_count'],
                'repos_active': repos_count,
                'lines_added': data['lines_added'],
                'lines_deleted': data['lines_deleted'],
                'first_commit_time': first_commit.strftime('%H:%M') if first_commit else None,
                'last_commit_time': last_commit.strftime('%H:%M') if last_commit else None,
                'work_span_hours': round(work_span_hours, 2),
                'commit_frequency': commit_frequency,
                'focus_score': focus_score,
                'primary_language': primary_language,
                'primary_category': primary_category,
                'languages_count': len(data['languages_used']),
                'late_night_commits': late_night_commits,
                'is_weekend': is_weekend,
                'repos_list': ','.join(sorted(data['repos_active']))[:100]  # Truncate for CSV
            })
        
        return processed_data
    
    def collect_activity_data(self, days_back=14):
        """Main method to collect GitHub activity data"""
        logger.info(f"🐙 Collecting GitHub activity data for {self.username}")
        
        # Load previous sync state
        sync_state = self.load_last_sync_state()
        
        # Calculate date range
        end_date = date.today()
        if sync_state.get('last_successful_sync'):
            # Sync from last successful date with 1 day overlap
            start_date = datetime.fromisoformat(sync_state['last_successful_sync']).date() - timedelta(days=1)
        else:
            # First run - get last N days
            start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"Syncing GitHub activity from {start_date} to {end_date}")
        
        try:
            # Get all repositories
            repos = self.get_all_repositories()
            active_repos = [repo for repo in repos if not repo.get('archived', False)]
            
            logger.info(f"Found {len(active_repos)} active repositories")
            
            # Collect commits from all repositories
            all_commits = []
            
            for repo in active_repos:
                repo_name = repo['name']
                logger.debug(f"Getting commits from {repo_name}")
                
                # Get commits since start date
                repo_commits = self.get_commits_for_repo(repo_name, start_date)
                all_commits.extend(repo_commits)
                
                # Rate limiting between repos
                time.sleep(0.1)
            
            logger.info(f"Collected {len(all_commits)} total commits from {len(active_repos)} repositories")
            
            # Analyze daily activity
            daily_data = self.analyze_daily_activity(all_commits, repos)
            
            # Update sync state
            sync_state.update({
                'last_successful_sync': end_date.isoformat(),
                'repos_discovered': len(repos),
                'last_sync_timestamp': datetime.now().isoformat()
            })
            self.save_sync_state(sync_state)
            
            logger.info(f"✅ GitHub data collection complete: {len(daily_data)} days of activity")
            return daily_data
            
        except Exception as e:
            logger.error(f"Failed to collect GitHub activity data: {e}")
            return []


def collect_github_activity(username, token):
    """Main function to collect GitHub activity data"""
    if not username or not token:
        logger.warning("GitHub username or token not provided, skipping GitHub data collection")
        return []
    
    try:
        collector = GitHubActivityCollector(username, token)
        return collector.collect_activity_data()
    except Exception as e:
        logger.error(f"GitHub data collection failed: {e}")
        return []


if __name__ == "__main__":
    # Test script
    import os
    
    username = os.getenv('_GITHUB_USERNAME')
    token = os.getenv('_GITHUB_TOKEN')

    if not username or not token:
        print("Please set _GITHUB_USERNAME and _GITHUB_TOKEN environment variables")
        exit(1)
    
    logging.basicConfig(level=logging.INFO)
    data = collect_github_activity(username, token)
    
    print(f"Collected {len(data)} days of GitHub activity:")
    for day in data[-5:]:  # Show last 5 days
        print(f"  {day['date']}: {day['commits_count']} commits, {day['repos_active']} repos, focus: {day['focus_score']}")