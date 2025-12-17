import React, { useState, useEffect, useRef } from 'react'
import './ChatPanel.css'

function ChatPanel({ onSendMessage, ws, sessionId: propSessionId, onSessionChange }) {
  // WebSocket is optional - used for real-time updates (Telegram messages, etc.)
  // Chat messages use REST API
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [availableSessions, setAvailableSessions] = useState([])
  const [availableModels, setAvailableModels] = useState([])
  const [sessionModel, setSessionModel] = useState('')
  const [sessionId, setSessionId] = useState(propSessionId || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
  const [isNewSession, setIsNewSession] = useState(!propSessionId)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const fileInputRef = useRef(null)
  const sessionIdRef = useRef(sessionId)

  useEffect(() => {
    sessionIdRef.current = sessionId
  }, [sessionId])

  useEffect(() => {
    if (ws) {
      const handleMessage = (event) => {
        const data = JSON.parse(event.data)
        
        if (data.type === 'chat_response') {
          setIsTyping(false)
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: data.response,
            timestamp: new Date(),
          }])
        } else if (data.type === 'telegram_message' || data.type === 'chatgpt_message') {
          // Handle incoming Telegram or ChatGPT messages
          if (data.session_id && data.session_id !== sessionIdRef.current) {
            return
          }
          const messageType = data.role === 'user' ? 'user' : 'assistant'
          const source = data.type === 'telegram_message' ? 'telegram' : 'chatgpt'
          const defaultSender = data.role === 'user' 
            ? (source === 'telegram' ? 'Telegram User' : 'User')
            : 'ARES'
          setMessages(prev => [...prev, {
            type: messageType,
            content: data.message,
            timestamp: new Date(),
            source: source,
            sender: data.sender || defaultSender,
          }])
        }
      }

      ws.addEventListener('message', handleMessage)
      return () => ws.removeEventListener('message', handleMessage)
    }
  }, [ws])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
      setInput(`Please review this file: ${file.name}`)
    }
  }

  const handleFileRemove = () => {
    setSelectedFile(null)
    setInput('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const readFileContent = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target.result)
      reader.onerror = reject
      reader.readAsText(file)
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() && !selectedFile) return

    let messageContent = input.trim()
    let fileContent = null

    // Handle file upload
    if (selectedFile) {
      try {
        fileContent = await readFileContent(selectedFile)
        if (!messageContent) {
          messageContent = `Please review this ${selectedFile.name} file`
        }
      } catch (error) {
        console.error('Failed to read file:', error)
        setMessages(prev => [...prev, {
          type: 'error',
          content: `Failed to read file: ${error.message}`,
          timestamp: new Date(),
        }])
        return
      }
    }

    const userMessage = {
      type: 'user',
      content: messageContent,
      file: selectedFile ? { name: selectedFile.name, content: fileContent } : null,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setIsTyping(true)

    // Send message via REST API
    try {
      const messageData = {
        message: messageContent,
        session_id: sessionId,
      }

      if (fileContent) {
        messageData.file_content = fileContent
        messageData.file_name = selectedFile.name
      }

      // Include auth token if available
      const headers = {
        'Content-Type': 'application/json',
      }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }

      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify(messageData),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to get response')
      }

      const data = await response.json()
      
      setIsTyping(false)
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: data.response || '',
        timestamp: new Date(),
      }])
    } catch (error) {
      console.error('Failed to send message:', error)
      setIsTyping(false)
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date(),
      }])
    }

    setInput('')
    setSelectedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
    inputRef.current?.focus()
  }

  useEffect(() => {
    // Load available sessions
    const loadSessions = async () => {
      try {
        const headers = {}
        if (window.authToken) {
          headers['Authorization'] = `Bearer ${window.authToken}`
        }
        const response = await fetch('/api/v1/sessions?limit=200', { headers })
        if (response.ok) {
          const data = await response.json()
          const ids = (data.sessions || []).map(s => s.session_id)
          setAvailableSessions(ids)
        }
      } catch (err) {
        console.error('Failed to load sessions:', err)
      }
    }
    loadSessions()
  }, [])

  useEffect(() => {
    const loadModels = async () => {
      try {
        const headers = {}
        if (window.authToken) {
          headers['Authorization'] = `Bearer ${window.authToken}`
        }
        const res = await fetch('/api/v1/models', { headers })
        if (res.ok) {
          const data = await res.json()
          setAvailableModels(data.models || [])
        }
      } catch (err) {
        console.error('Failed to load models:', err)
      }
    }
    loadModels()
  }, [])

  useEffect(() => {
    const loadSessionMeta = async () => {
      try {
        const headers = {}
        if (window.authToken) {
          headers['Authorization'] = `Bearer ${window.authToken}`
        }
        const res = await fetch(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, { headers })
        if (res.ok) {
          const data = await res.json()
          setSessionModel(data.model || '')
        } else {
          setSessionModel('')
        }
      } catch (err) {
        console.error('Failed to load session metadata:', err)
      }
    }
    if (sessionId) loadSessionMeta()
  }, [sessionId])

  const updateSessionModel = async (model) => {
    setSessionModel(model)
    try {
      const headers = { 'Content-Type': 'application/json' }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      await fetch(`/api/v1/sessions/${encodeURIComponent(sessionId)}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ model: model || null }),
      })
    } catch (err) {
      console.error('Failed to update session model:', err)
    }
  }

  useEffect(() => {
    // Update sessionId when prop changes
    if (propSessionId && propSessionId !== sessionId) {
      setSessionId(propSessionId)
      setIsNewSession(false)
    }
  }, [propSessionId])

  useEffect(() => {
    // Load conversation history when sessionId changes
    const loadHistory = async () => {
      try {
        const headers = {}
        if (window.authToken) {
          headers['Authorization'] = `Bearer ${window.authToken}`
        }
        const response = await fetch(`/api/v1/conversations?session_id=${sessionId}&limit=50`, { headers })
        if (response.ok) {
          const data = await response.json()
          if (data.conversations && data.conversations.length > 0) {
            const historyMessages = data.conversations.map(conv => ({
              type: conv.role === 'user' ? 'user' : 'assistant',
              content: conv.message,
              timestamp: new Date(conv.created_at),
            }))
            setMessages(historyMessages)
            setIsNewSession(false)
          } else {
            setMessages([])
          }
        }
      } catch (err) {
        console.error('Failed to load conversation history:', err)
      }
    }
    
    loadHistory()
  }, [sessionId])

  const handleSessionSelect = (e) => {
    const selectedId = e.target.value
    if (selectedId === 'new') {
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      setSessionId(newSessionId)
      setIsNewSession(true)
      setMessages([])
      if (onSessionChange) {
        onSessionChange(newSessionId)
      }
    } else if (selectedId && selectedId !== sessionId) {
      setSessionId(selectedId)
      setIsNewSession(false)
      if (onSessionChange) {
        onSessionChange(selectedId)
      }
    }
  }

  const handleNewSession = () => {
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    setSessionId(newSessionId)
    setIsNewSession(true)
    setMessages([])
    if (onSessionChange) {
      onSessionChange(newSessionId)
    }
  }

  const formatTime = (date) => {
    return new Date(date).toLocaleTimeString()
  }

  return (
    <div className="panel chat-panel">
      <div className="chat-header">
        <h2>Chat with ARES</h2>
        <div className="session-selector-container">
          <select
            value={sessionModel}
            onChange={(e) => updateSessionModel(e.target.value)}
            className="session-selector"
            title="Per-session model"
          >
            <option value="">Model: default</option>
            {availableModels.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <select
            value={isNewSession && !availableSessions.includes(sessionId) ? 'new' : sessionId}
            onChange={handleSessionSelect}
            className="session-selector"
            title="Select conversation session"
          >
            <option value="new">+ New Conversation</option>
            {availableSessions.map((sid) => (
              <option key={sid} value={sid}>
                {sid.replace('session_', '').substring(0, 20)}...
              </option>
            ))}
          </select>
          <button
            onClick={handleNewSession}
            className="new-session-button"
            title="Start new conversation"
          >
            ➕ New
          </button>
        </div>
      </div>
      
      {isNewSession && messages.length === 0 && (
        <div className="session-info-banner">
          Starting new conversation session: {sessionId.substring(0, 30)}...
        </div>
      )}
      
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="empty-state">
            Start a conversation with ARES...
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`chat-message ${msg.type}`}>
              <div className="message-header">
                <span className="message-sender">
                  {msg.source === 'telegram' 
                    ? (msg.sender || (msg.type === 'user' ? 'Telegram User' : 'ARES'))
                    : msg.source === 'chatgpt'
                    ? (msg.sender || (msg.type === 'user' ? 'User' : 'ARES'))
                    : (msg.type === 'user' ? 'You' : msg.type === 'error' ? 'Error' : 'ARES')
                  }
                  {msg.source === 'telegram' && ' 📱'}
                  {msg.source === 'chatgpt' && ' 🌐'}
                </span>
                <span className="message-time">{formatTime(msg.timestamp)}</span>
              </div>
              <div className="message-content">
                {msg.content}
                {msg.file && (
                  <div className="file-attachment">
                    <div className="file-info">
                      📎 <strong>{msg.file.name}</strong>
                    </div>
                    <pre className="file-preview">
                      {msg.file.content.length > 1000
                        ? msg.file.content.substring(0, 1000) + '...'
                        : msg.file.content
                      }
                    </pre>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        
        {isTyping && (
          <div className="chat-message assistant typing">
            <div className="message-header">
              <span className="message-sender">ARES</span>
            </div>
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="chat-input-form">
        <div className="chat-input-container">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={selectedFile ? "Add a message about the file..." : "Type your message..."}
            className="chat-input"
            disabled={isTyping}
          />
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            accept=".py,.js,.jsx,.ts,.tsx,.css,.html,.md,.txt,.json,.xml,.yaml,.yml"
            style={{ display: 'none' }}
            id="file-input"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="file-attach-button"
            title="Attach file for review"
          >
            📎
          </button>
        </div>

        {selectedFile && (
          <div className="selected-file">
            <div className="file-info">
              📎 <strong>{selectedFile.name}</strong> ({(selectedFile.size / 1024).toFixed(1)} KB)
            </div>
            <button
              type="button"
              onClick={handleFileRemove}
              className="file-remove-button"
              title="Remove file"
            >
              ✕
            </button>
          </div>
        )}

          <button
            type="submit"
            className="chat-send-button"
            disabled={(!input.trim() && !selectedFile) || isTyping}
          >
            Send
          </button>
      </form>
    </div>
  )
}

export default ChatPanel

