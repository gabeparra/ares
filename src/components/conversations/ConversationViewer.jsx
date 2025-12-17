import React, { useState, useEffect } from 'react'
import '../../styles/ConversationViewer.css'

function ConversationViewer({ sessionId, onClose, onContinueConversation }) {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (sessionId) {
      loadConversations()
    }
  }, [sessionId])

  const loadConversations = async () => {
    setLoading(true)
    try {
      const headers = {}
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch(`/api/v1/conversations?session_id=${sessionId}&limit=100`, { headers })
      if (response.ok) {
        const data = await response.json()
        setConversations(data.conversations || [])
      }
    } catch (err) {
      console.error('Failed to load conversations:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatTime = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleString()
  }

  if (!sessionId) {
    return (
      <div className="conversation-viewer-empty">
        Select a conversation session to view
      </div>
    )
  }

  return (
    <div className="conversation-viewer">
      <div className="viewer-header">
        <h3>Conversation History</h3>
        <div className="session-info">
          <span className="session-id-display">Session: {sessionId.substring(0, 20)}...</span>
        </div>
        <div className="viewer-actions">
          {onContinueConversation && (
            <button
              className="continue-conversation-button"
              onClick={() => onContinueConversation(sessionId)}
              title="Continue this conversation"
            >
              💬 Continue Conversation
            </button>
          )}
          {onClose && (
            <button className="close-viewer" onClick={onClose}>
              ✕
            </button>
          )}
        </div>
      </div>

      <div className="conversation-messages">
        {loading ? (
          <div className="loading">Loading conversation...</div>
        ) : conversations.length === 0 ? (
          <div className="empty-state">No messages in this conversation</div>
        ) : (
          conversations.map((conv, idx) => (
            <div key={idx} className={`conv-message ${conv.role}`}>
              <div className="conv-message-header">
                <span className="conv-role">
                  {conv.role === 'user' ? '👤 You' : '🤖 ARES'}
                </span>
                <span className="conv-time">{formatTime(conv.created_at)}</span>
              </div>
              <div className="conv-content">{conv.message}</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default ConversationViewer

