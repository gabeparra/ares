"""
Django management command for hourly memory revision.

This command should be run every hour (via cron) to:
- Re-analyze active conversations
- Extract new memories while maintaining important existing values
- Avoid re-processing conversations that were recently revised

Usage:
    python3 manage.py revise_memories_hourly
    python3 manage.py revise_memories_hourly --limit 20
    python3 manage.py revise_memories_hourly --auto-apply
"""

from django.core.management.base import BaseCommand
from ares_mind.memory_extraction import (
    revise_memories_hourly,
    auto_apply_high_confidence_memories,
)


class Command(BaseCommand):
    help = 'Hourly memory revision: Re-analyze conversations to extract new memories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Number of sessions to process per run (default: 20)',
        )
        parser.add_argument(
            '--auto-apply',
            action='store_true',
            help='Automatically apply high-confidence memory spots after revision',
        )
        parser.add_argument(
            '--confidence-threshold',
            type=float,
            default=0.8,
            help='Confidence threshold for auto-apply (default: 0.8)',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        auto_apply = options['auto_apply']
        confidence_threshold = options['confidence_threshold']

        self.stdout.write('Starting hourly memory revision...')
        
        # Run hourly revision
        stats = revise_memories_hourly(limit=limit)
        
        if 'error' in stats:
            self.stdout.write(
                self.style.ERROR(f'Revision failed: {stats["error"]}')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Revision complete: {stats["sessions_processed"]} sessions processed, '
                f'{stats["total_extracted"]} memories extracted'
            )
        )
        
        if stats.get('sessions_skipped', 0) > 0:
            self.stdout.write(
                f'Skipped {stats["sessions_skipped"]} sessions (recently revised)'
            )
        
        if stats.get('errors'):
            self.stdout.write(
                self.style.WARNING(f'{len(stats["errors"])} errors occurred:')
            )
            for error in stats['errors'][:5]:  # Show first 5 errors
                self.stdout.write(f'  - {error}')
            if len(stats['errors']) > 5:
                self.stdout.write(f'  ... and {len(stats["errors"]) - 5} more')
        
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
                self.stdout.write(
                    self.style.WARNING(f'{len(errors)} errors during auto-apply')
                )

