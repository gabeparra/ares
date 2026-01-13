"""
Django management command to process conversations and extract memories.

Usage:
    python3 manage.py process_memories
    python3 manage.py process_memories --limit 50
    python3 manage.py process_memories --auto-apply
    python3 manage.py process_memories --session-id session_123
    python3 manage.py process_memories --reprocess  # Re-process all sessions
    python3 manage.py process_memories --all  # Process all unprocessed sessions (no limit)
"""

from django.core.management.base import BaseCommand
from django.db.models import Count
from api.models import ChatSession, MemorySpot
from ares_mind.memory_extraction import (
    extract_memories_from_conversation,
    auto_apply_high_confidence_memories,
)


class Command(BaseCommand):
    help = 'Process conversations to extract memories and apply high-confidence ones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Number of sessions to process (default: 50)',
        )
        parser.add_argument(
            '--min-messages',
            type=int,
            default=5,
            help='Minimum messages required in a session (default: 5)',
        )
        parser.add_argument(
            '--session-id',
            type=str,
            help='Process a specific session ID',
        )
        parser.add_argument(
            '--auto-apply',
            action='store_true',
            help='Automatically apply high-confidence memory spots',
        )
        parser.add_argument(
            '--confidence-threshold',
            type=float,
            default=0.8,
            help='Confidence threshold for auto-apply (default: 0.8)',
        )
        parser.add_argument(
            '--user-id',
            type=str,
            default='default',
            help='User ID to process (default: default)',
        )
        parser.add_argument(
            '--reprocess',
            action='store_true',
            help='Re-process sessions with "extracted" status only (will NOT touch reviewed/applied/rejected sessions)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all unprocessed sessions (ignores --limit)',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        min_messages = options['min_messages']
        session_id = options.get('session_id')
        auto_apply = options['auto_apply']
        confidence_threshold = options['confidence_threshold']
        user_id = options['user_id']
        reprocess = options['reprocess']
        process_all = options['all']

        if session_id:
            # Process specific session
            self.stdout.write(f'Processing session: {session_id}')
            count, errors = extract_memories_from_conversation(
                session_id=session_id,
                user_id=user_id,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Extracted {count} memory spots from session {session_id}'
                )
            )
            if errors:
                for error in errors:
                    self.stdout.write(self.style.WARNING(f'  Error: {error}'))
        else:
            # Process sessions
            # Always exclude sessions that have been reviewed, applied, or rejected
            # These are final states and should never be reprocessed
            final_status_sessions = set(
                MemorySpot.objects.exclude(session__isnull=True)
                .filter(status__in=[
                    MemorySpot.STATUS_REVIEWED,
                    MemorySpot.STATUS_APPLIED,
                    MemorySpot.STATUS_REJECTED
                ])
                .values_list('session_id', flat=True)
                .distinct()
            )
            
            if reprocess:
                self.stdout.write('Finding sessions to re-process (excluding reviewed/applied/rejected)...')
                # Re-process sessions that only have "extracted" status or no memories
                # Get sessions with "extracted" status only
                extracted_only_sessions = set(
                    MemorySpot.objects.exclude(session__isnull=True)
                    .filter(status=MemorySpot.STATUS_EXTRACTED)
                    .values_list('session_id', flat=True)
                    .distinct()
                )
                
                # Get sessions that have extracted memories but no final status memories
                sessions = ChatSession.objects.exclude(
                    session_id__in=final_status_sessions
                ).filter(
                    session_id__in=extracted_only_sessions
                ).annotate(
                    message_count=Count('messages')
                ).filter(
                    message_count__gte=min_messages
                ).order_by('-updated_at')
            else:
                self.stdout.write('Finding unprocessed sessions (excluding reviewed/applied/rejected)...')
                # Get sessions that haven't been processed at all (no MemorySpots)
                # We exclude final_status_sessions, but we can process sessions with
                # only "extracted" status or no MemorySpots at all
                all_processed_sessions = set(
                    MemorySpot.objects.exclude(session__isnull=True)
                    .values_list('session_id', flat=True)
                    .distinct()
                )
                
                # Get sessions with enough messages that:
                # 1. Have NOT been reviewed/applied/rejected (final_status_sessions)
                # 2. Have NOT been processed at all (no MemorySpots)
                sessions = ChatSession.objects.exclude(
                    session_id__in=final_status_sessions
                ).exclude(
                    session_id__in=all_processed_sessions
                ).annotate(
                    message_count=Count('messages')
                ).filter(
                    message_count__gte=min_messages
                ).order_by('-updated_at')
            
            # Apply limit unless --all is specified
            if not process_all:
                sessions = sessions[:limit]
            
            # Convert to list to get accurate count
            sessions_list = list(sessions)
            total_sessions = len(sessions_list)
            
            if total_sessions == 0:
                self.stdout.write(self.style.WARNING('No sessions found to process'))
            else:
                self.stdout.write(f'Found {total_sessions} sessions to process')
                
                total_extracted = 0
                total_errors = 0
                
                for session in sessions_list:
                    self.stdout.write(f'Processing session: {session.session_id} ({session.message_count} messages)')
                    count, errors = extract_memories_from_conversation(
                        session_id=session.session_id,
                        user_id=user_id,
                    )
                    total_extracted += count
                    total_errors += len(errors)
                    
                    if errors:
                        for error in errors:
                            self.stdout.write(self.style.WARNING(f'  Error: {error}'))
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Processed {total_sessions} sessions, extracted {total_extracted} memory spots'
                    )
                )
        
        # Auto-apply high-confidence memories if requested
        if auto_apply:
            self.stdout.write('Auto-applying high-confidence memory spots...')
            applied_count, errors = auto_apply_high_confidence_memories(confidence_threshold)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Applied {applied_count} high-confidence memory spots'
                )
            )
            if errors:
                for error in errors:
                    self.stdout.write(self.style.WARNING(f'  Error: {error}'))

