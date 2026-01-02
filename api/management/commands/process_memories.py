"""
Django management command to process conversations and extract memories.

Usage:
    python3 manage.py process_memories
    python3 manage.py process_memories --limit 10
    python3 manage.py process_memories --auto-apply
    python3 manage.py process_memories --session-id session_123
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
            default=10,
            help='Number of sessions to process (default: 10)',
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

    def handle(self, *args, **options):
        limit = options['limit']
        min_messages = options['min_messages']
        session_id = options.get('session_id')
        auto_apply = options['auto_apply']
        confidence_threshold = options['confidence_threshold']
        user_id = options['user_id']

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
            # Process unprocessed sessions
            self.stdout.write('Finding unprocessed sessions...')
            
            # Get sessions that haven't been processed
            processed_sessions = set(
                MemorySpot.objects.exclude(session__isnull=True)
                .values_list('session_id', flat=True)
                .distinct()
            )
            
            # Get sessions with enough messages
            sessions = ChatSession.objects.exclude(
                session_id__in=processed_sessions
            ).annotate(
                message_count=Count('messages')
            ).filter(
                message_count__gte=min_messages
            ).order_by('-updated_at')[:limit]
            
            total_sessions = sessions.count()
            self.stdout.write(f'Found {total_sessions} sessions to process')
            
            total_extracted = 0
            total_errors = 0
            
            for session in sessions:
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

