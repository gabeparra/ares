import React, { useState, useEffect } from 'react'
import '../../styles/ConversationList.css'

function ConversationList({ onSelectSession, selectedSessionId }) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    setLoading(true)
    try {
      const headers = {}
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch('/api/v1/sessions?limit=200', { headers })
      if (response.ok) {
        const data = await response.json()
        setSessions(data.sessions || [])
      }
    } catch (err) {
      console.error('Failed to load sessions:', err)
    } finally {
      setLoading(false)
    }
  }

  const updateSession = async (sessionId, patch) => {
    try {
      const headers = { 'Content-Type': 'application/json' }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify(patch),
      })
      if (response.ok) {
        await loadSessions()
      }
    } catch (err) {
      console.error('Failed to update session:', err)
    }
  }

  const deleteSession = async (sessionId) => {
    const ok = window.confirm('Delete this session and all its messages?')
    if (!ok) return
    try {
      const headers = {}
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, {
        method: 'DELETE',
        headers,
      })
      if (response.ok) {
        await loadSessions()
      }
    } catch (err) {
      console.error('Failed to delete session:', err)
    }
  }

  const exportSession = async (sessionId, format) => {
    try {
      const headers = {}
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch(`/api/v1/sessions/${encodeURIComponent(sessionId)}/export?format=${format}`, { headers })
      if (!response.ok) return
      const data = await response.json()
      const blob = new Blob([data.content || JSON.stringify(data, null, 2)], {
        type: format === 'md' ? 'text/markdown' : 'application/json',
      })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `${sessionId}.${format === 'md' ? 'md' : 'json'}`
      document.body.appendChild(a)
      a.click()
      a.remove()
    } catch (err) {
      console.error('Failed to export session:', err)
    }
  }

  const filteredSessions = sessions.filter(session => {
    const hay = `${session.session_id} ${session.title || ''}`.toLowerCase()
    return hay.includes(searchQuery.toLowerCase())
  })

  return (
    <div className="conversation-list">
      <div className="list-header">
        <h3>Conversation Sessions</h3>
        <button className="refresh-btn" onClick={loadSessions} title="Refresh">
          🔄
        </button>
      </div>

      <div className="search-box">
        <input
          type="text"
          placeholder="Search sessions..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      <div className="sessions-container">
        {loading ? (
          <div className="loading">Loading sessions...</div>
        ) : filteredSessions.length === 0 ? (
          <div className="empty-state">
            {searchQuery ? 'No sessions found' : 'No conversation history yet'}
          </div>
        ) : (
          filteredSessions.map((session) => {
            const sessionId = session.session_id
            return (
              <div
                key={sessionId}
                className={`session-card ${selectedSessionId === sessionId ? 'selected' : ''}`}
                onClick={() => onSelectSession && onSelectSession(sessionId)}
              >
                <div className="session-title">
                  {session.pinned ? '📌 ' : ''}{session.title || sessionId.replace('session_', '').substring(0, 25)}
                </div>
                <div className="session-actions">
                  <button
                    className="mini-btn"
                    onClick={(e) => { e.stopPropagation(); updateSession(sessionId, { pinned: !session.pinned }) }}
                    title={session.pinned ? 'Unpin' : 'Pin'}
                  >
                    {session.pinned ? '📌' : '📍'}
                  </button>
                  <button
                    className="mini-btn"
                    onClick={(e) => {
                      e.stopPropagation()
                      const title = window.prompt('Session title:', session.title || '')
                      if (title !== null) updateSession(sessionId, { title })
                    }}
                    title="Rename"
                  >
                    ✏️
                  </button>
                  <button className="mini-btn" onClick={(e) => { e.stopPropagation(); exportSession(sessionId, 'md') }} title="Export Markdown">
                    ⬇️
                  </button>
                  <button className="mini-btn danger" onClick={(e) => { e.stopPropagation(); deleteSession(sessionId) }} title="Delete session">
                    🗑️
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

export default ConversationList

