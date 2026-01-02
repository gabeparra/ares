import React, { useState, useEffect } from 'react';
import { apiGet } from '../../services/api';
import './CalendarPanel.css';

function CalendarPanel() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [authorizationUrl, setAuthorizationUrl] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiGet('/api/v1/calendar/status');
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      console.error('Failed to load calendar status:', err);
      setError(err.message || 'Failed to load calendar status');
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async () => {
    setError(null);
    try {
      const response = await apiGet('/api/v1/calendar/connect');
      const data = await response.json();
      if (data.authorization_url) {
        setAuthorizationUrl(data.authorization_url);
        // Open in new window
        window.open(data.authorization_url, 'google-calendar-auth', 'width=600,height=700');
      }
    } catch (err) {
      console.error('Failed to initiate connection:', err);
      setError(err.message || 'Failed to initiate Google Calendar connection');
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Are you sure you want to disconnect Google Calendar?')) {
      return;
    }
    setError(null);
    try {
      const headers = {
        'Content-Type': 'application/json',
      };
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`;
      }
      const response = await fetch('/api/v1/calendar/disconnect', {
        method: 'POST',
        headers,
      });
      if (response.ok) {
        await loadStatus();
        setEvents([]);
      } else {
        const data = await response.json();
        setError(data.error || 'Failed to disconnect');
      }
    } catch (err) {
      console.error('Failed to disconnect:', err);
      setError(err.message || 'Failed to disconnect');
    }
  };

  const loadEvents = async () => {
    setEventsLoading(true);
    setError(null);
    try {
      const now = new Date();
      const nextWeek = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
      const response = await apiGet(
        `/api/v1/calendar/events?start=${now.toISOString()}&end=${nextWeek.toISOString()}&max_results=20`
      );
      const data = await response.json();
      setEvents(data.events || []);
    } catch (err) {
      console.error('Failed to load events:', err);
      setError(err.message || 'Failed to load calendar events');
    } finally {
      setEventsLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      const headers = {
        'Content-Type': 'application/json',
      };
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`;
      }
      const response = await fetch('/api/v1/calendar/sync', {
        method: 'POST',
        headers,
      });
      if (response.ok) {
        const data = await response.json();
        alert(
          `Sync completed! Created ${data.tasks_created} tasks, updated ${data.tasks_updated} tasks.`
        );
        await loadStatus();
      } else {
        const data = await response.json();
        setError(data.error || 'Failed to sync calendar');
      }
    } catch (err) {
      console.error('Failed to sync calendar:', err);
      setError(err.message || 'Failed to sync calendar');
    } finally {
      setSyncing(false);
    }
  };

  const formatEventTime = (timeStr) => {
    if (!timeStr) return 'All day';
    try {
      const date = new Date(timeStr);
      return date.toLocaleString();
    } catch {
      return timeStr;
    }
  };

  if (loading) {
    return (
      <div className="panel panel-fill">
        <div className="calendar-panel">
          <div className="calendar-loading">Loading calendar status...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="panel panel-fill">
      <div className="calendar-panel">
        <div className="calendar-header">
          <h2>Google Calendar Integration</h2>
          <button onClick={loadStatus} className="btn-refresh" title="Refresh status">
            ↻
          </button>
        </div>

        {error && (
          <div className="calendar-error">
            <strong>Error:</strong> {error}
          </div>
        )}

        <div className="calendar-status-section">
          <h3>Connection Status</h3>
          {status ? (
            <div className="status-info">
              <div className="status-item">
                <span className="status-label">Connected:</span>
                <span className={`status-value ${status.connected ? 'connected' : 'disconnected'}`}>
                  {status.connected ? 'Yes' : 'No'}
                </span>
              </div>
              {status.enabled !== undefined && (
                <div className="status-item">
                  <span className="status-label">Enabled:</span>
                  <span className="status-value">{status.enabled ? 'Yes' : 'No'}</span>
                </div>
              )}
              {status.calendar_id && (
                <div className="status-item">
                  <span className="status-label">Calendar ID:</span>
                  <span className="status-value">{status.calendar_id}</span>
                </div>
              )}
              {status.last_sync_at && (
                <div className="status-item">
                  <span className="status-label">Last Sync:</span>
                  <span className="status-value">{new Date(status.last_sync_at).toLocaleString()}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="status-info">No status available</div>
          )}

          <div className="calendar-actions">
            {status?.connected ? (
              <>
                <button onClick={handleDisconnect} className="btn-disconnect">
                  Disconnect
                </button>
                <button onClick={handleSync} className="btn-sync" disabled={syncing}>
                  {syncing ? 'Syncing...' : 'Sync Calendar'}
                </button>
                <button onClick={loadEvents} className="btn-load-events" disabled={eventsLoading}>
                  {eventsLoading ? 'Loading...' : 'Load Events'}
                </button>
              </>
            ) : (
              <button onClick={handleConnect} className="btn-connect">
                Connect Google Calendar
              </button>
            )}
          </div>
        </div>

        {authorizationUrl && (
          <div className="calendar-auth-info">
            <p>
              <strong>Authorization window opened.</strong> Please complete the authorization in the popup
              window. Once done, click "Refresh status" to update the connection status.
            </p>
            <button onClick={() => setAuthorizationUrl(null)} className="btn-dismiss">
              Dismiss
            </button>
          </div>
        )}

        {events.length > 0 && (
          <div className="calendar-events-section">
            <h3>Upcoming Events ({events.length})</h3>
            <div className="events-list">
              {events.map((event) => (
                <div key={event.id} className="event-item">
                  <div className="event-title">{event.title || 'No Title'}</div>
                  <div className="event-time">{formatEventTime(event.start)}</div>
                  {event.location && (
                    <div className="event-location">📍 {event.location}</div>
                  )}
                  {event.description && (
                    <div className="event-description">{event.description}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="calendar-info-section">
          <h3>How to Use</h3>
          <div className="info-content">
            <p>
              <strong>1. Connect:</strong> Click "Connect Google Calendar" to authorize ARES to access your
              calendar.
            </p>
            <p>
              <strong>2. Create Scheduled Tasks:</strong> Add events to your Google Calendar with these
              patterns:
            </p>
            <ul>
              <li>
                <code>ARES: Good Morning</code> - Triggers a good morning message with your day's schedule
              </li>
              <li>
                <code>ARES: [Task Name]</code> - Creates a custom task
              </li>
            </ul>
            <p>
              <strong>3. Sync:</strong> Click "Sync Calendar" to create scheduled tasks from your calendar
              events.
            </p>
            <p>
              <strong>4. Automation:</strong> Set up a cron job or systemd timer to run{' '}
              <code>python3 manage.py process_scheduled_tasks</code> periodically to execute scheduled
              tasks.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CalendarPanel;

