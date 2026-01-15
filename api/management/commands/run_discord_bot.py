"""
Django management command to run the Discord bot.

Usage:
    python manage.py run_discord_bot
    python manage.py run_discord_bot --daemon
    python manage.py run_discord_bot --no-monitor
"""

from django.core.management.base import BaseCommand
import logging
import os
import time

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the Discord bot with health monitoring'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon (keep running)',
        )
        parser.add_argument(
            '--no-monitor',
            action='store_true',
            help='Disable health monitor (not recommended)',
        )

    def handle(self, *args, **options):
        bot_token = os.getenv('DISCORD_BOT_TOKEN')
        if not bot_token:
            self.stdout.write(
                self.style.ERROR('DISCORD_BOT_TOKEN not configured in environment')
            )
            return

        from api.discord_bot import (
            start_discord_bot,
            start_discord_bot_with_monitor,
            stop_discord_bot_with_monitor,
            is_discord_bot_running,
            is_health_monitor_running,
            get_discord_bot_status,
        )

        use_monitor = not options.get('no_monitor', False)

        if use_monitor:
            self.stdout.write(self.style.SUCCESS('Starting Discord bot with health monitor...'))
            success = start_discord_bot_with_monitor()
        else:
            self.stdout.write(self.style.WARNING('Starting Discord bot WITHOUT health monitor...'))
            success = start_discord_bot()

        if success:
            self.stdout.write(self.style.SUCCESS('Discord bot started successfully!'))

            # Wait for the bot to connect
            self.stdout.write('Waiting for bot to connect...')
            for i in range(10):
                time.sleep(1)
                status = get_discord_bot_status()
                if status['ready']:
                    self.stdout.write(self.style.SUCCESS(
                        f"Bot connected! Guilds: {status['guilds']}, Latency: {status['latency_ms']}ms"
                    ))
                    break
            else:
                self.stdout.write(self.style.WARNING('Bot not yet ready, continuing anyway...'))

            if use_monitor:
                self.stdout.write(f"Health monitor running: {is_health_monitor_running()}")

            if options['daemon']:
                self.stdout.write('Running as daemon. Press Ctrl+C to stop.')
                self._run_daemon_loop(is_discord_bot_running, get_discord_bot_status, use_monitor)
            else:
                self.stdout.write('Bot is running in background. Use Ctrl+C to exit.')
                self._run_daemon_loop(is_discord_bot_running, get_discord_bot_status, use_monitor)

            # Cleanup
            self.stdout.write(self.style.WARNING('\nStopping bot...'))
            stop_discord_bot_with_monitor()
            self.stdout.write(self.style.SUCCESS('Bot stopped.'))
        else:
            self.stdout.write(
                self.style.ERROR('Failed to start Discord bot')
            )

    def _run_daemon_loop(self, is_running_func, get_status_func, has_monitor):
        """Main daemon loop that monitors bot health."""
        try:
            consecutive_failures = 0
            last_status_log = 0

            while True:
                time.sleep(5)

                if is_running_func():
                    consecutive_failures = 0

                    # Log status periodically (every 5 minutes)
                    now = time.time()
                    if now - last_status_log > 300:
                        status = get_status_func()
                        logger.info(
                            f"[DISCORD] Status: guilds={status['guilds']}, "
                            f"latency={status['latency_ms']}ms, "
                            f"uptime={status['uptime_seconds']}s, "
                            f"restarts={status['restart_count']}"
                        )
                        last_status_log = now
                else:
                    consecutive_failures += 1
                    status = get_status_func()
                    logger.warning(
                        f"[DISCORD] Bot not running (failure {consecutive_failures}): "
                        f"last_error={status['last_error']}"
                    )

                    # If health monitor is enabled, it will handle restarts
                    # If not, exit after 60 seconds of failures
                    if not has_monitor and consecutive_failures > 12:
                        logger.error('[DISCORD] Bot stopped and no health monitor. Exiting...')
                        break

                    # With health monitor, give it more time to recover
                    if has_monitor and consecutive_failures > 24:  # 2 minutes
                        logger.error('[DISCORD] Bot failed to recover. Exiting...')
                        break

        except KeyboardInterrupt:
            pass  # Clean exit on Ctrl+C

