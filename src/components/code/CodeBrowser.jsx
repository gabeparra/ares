import React, { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import './CodeBrowser.css'

function CodeBrowser() {
  const [files, setFiles] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileContent, setFileContent] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [sessionId, setSessionId] = useState(() => {
    // Use a dedicated session for code browser
    const today = new Date()
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const day = String(today.getDate()).padStart(2, '0')
    return `code_review_${year}-${month}-${day}`
  })
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    loadFiles()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadFiles = async () => {
    setLoading(true)
    try {
      const headers = {}
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch('/api/v1/code/files', { headers })
      if (response.ok) {
        const data = await response.json()
        setFiles(data.files || [])
      } else {
        console.error('Failed to load files:', response.status)
      }
    } catch (err) {
      console.error('Failed to load files:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleFileSelect = async (filePath) => {
    setLoading(true)
    setSelectedFile(filePath)
    try {
      const headers = {}
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }
      const response = await fetch(
        `/api/v1/code/file?file_path=${encodeURIComponent(filePath)}`,
        { headers }
      )
      if (response.ok) {
        const data = await response.json()
        setFileContent(data)
      } else {
        setFileContent(null)
      }
    } catch (err) {
      console.error('Failed to read file:', err)
      setFileContent(null)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (query) => {
    setSearchQuery(query)
  }

  const sendFileToChat = (filePath, content) => {
    const fileData = fileContent || content
    if (!fileData) return

    const message = `Please review this file: ${filePath}\n\n\`\`\`${fileData.language || 'text'}\n${fileData.content}\n\`\`\``
    setInput(message)
    inputRef.current?.focus()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage = {
      type: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setIsTyping(true)
    setInput('')

    try {
      const headers = {
        'Content-Type': 'application/json',
      }
      if (window.authToken) {
        headers['Authorization'] = `Bearer ${window.authToken}`
      }

      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: userMessage.content,
          session_id: sessionId,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to get response')
      }

      const data = await response.json()
      
      setIsTyping(false)
      const assistantMessage = {
        type: 'assistant',
        content: data.response || '',
        timestamp: new Date(),
      }
      
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Failed to send message:', error)
      setIsTyping(false)
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date(),
      }])
    }
  }

  const filteredFiles = files.filter(file =>
    file.path.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Group files by directory for better organization
  const groupedFiles = {}
  filteredFiles.forEach(file => {
    const dir = file.path.split('/').slice(0, -1).join('/') || '/'
    if (!groupedFiles[dir]) {
      groupedFiles[dir] = []
    }
    groupedFiles[dir].push(file)
  })

  const formatTime = (date) => {
    return new Date(date).toLocaleTimeString()
  }

  return (
    <div className="code-browser-panel panel">
      <div className="code-browser-header">
        <h2>Code Browser</h2>
        <button onClick={loadFiles} className="refresh-button" title="Refresh file list">
          🔄
        </button>
      </div>

      <div className="code-browser-content">
        {/* File Browser Sidebar */}
        <div className="code-browser-sidebar">
          <div className="code-search-box">
            <input
              type="text"
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
            />
          </div>

          <div className="file-list">
            {loading && !fileContent && <div className="loading">Loading files...</div>}
            {Object.keys(groupedFiles).map(dir => (
              <div key={dir} className="file-group">
                {dir !== '/' && (
                  <div className="file-group-header">
                    📁 {dir}
                  </div>
                )}
                {groupedFiles[dir].map((file) => (
                  <div
                    key={file.path}
                    className={`file-item ${selectedFile === file.path ? 'selected' : ''}`}
                    onClick={() => handleFileSelect(file.path)}
                    title={file.path}
                  >
                    <span className="file-icon">
                      {file.extension === '.py' ? '🐍' :
                       file.extension === '.js' || file.extension === '.jsx' ? '📜' :
                       file.extension === '.ts' || file.extension === '.tsx' ? '📘' :
                       file.extension === '.css' ? '🎨' :
                       file.extension === '.html' ? '🌐' :
                       file.extension === '.md' ? '📝' :
                       file.extension === '.json' ? '📋' :
                       file.extension === '.yaml' || file.extension === '.yml' ? '⚙️' :
                       '📄'}
                    </span>
                    <span className="file-name">{file.name}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Code Viewer */}
        <div className="code-viewer">
          {loading && fileContent === null && (
            <div className="loading">Loading file...</div>
          )}
          
          {fileContent && (
            <div className="file-content">
              <div className="file-header">
                <span className="file-path">{fileContent.file_path}</span>
                <button
                  onClick={() => sendFileToChat(fileContent.file_path, fileContent)}
                  className="send-to-chat-button"
                  title="Send file to chat for review"
                >
                  💬 Review in Chat
                </button>
              </div>
              <div className="code-block-container">
                <SyntaxHighlighter
                  style={oneDark}
                  language={fileContent.language || 'text'}
                  PreTag="div"
                  customStyle={{
                    margin: 0,
                    borderRadius: 0,
                    fontSize: '0.9em',
                    padding: '15px',
                  }}
                >
                  {fileContent.content}
                </SyntaxHighlighter>
              </div>
            </div>
          )}

          {!fileContent && !loading && (
            <div className="empty-state">
              Select a file to view its contents
            </div>
          )}
        </div>

        {/* Chat Panel */}
        <div className="code-chat-panel">
          <div className="chat-header">
            <h3>Ask about Code</h3>
          </div>
          
          <div className="chat-messages">
            {messages.length === 0 ? (
              <div className="empty-state">
                Select a file and ask questions about it...
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`chat-message ${msg.type}`}>
                  <div className="message-header">
                    <span className="message-sender">
                      {msg.type === 'user' ? 'You' : msg.type === 'error' ? 'Error' : 'ARES'}
                    </span>
                    <span className="message-time">{formatTime(msg.timestamp)}</span>
                  </div>
                  <div className="message-content">
                    {msg.type === 'assistant' ? (
                      <ReactMarkdown
                        components={{
                          code({ inline, className, children, ...props }) {
                            const match = /language-(\w+)/.exec(className || '')
                            const codeString = String(children).replace(/\n$/, '')
                            return !inline && match ? (
                              <SyntaxHighlighter
                                style={oneDark}
                                language={match[1]}
                                PreTag="div"
                                customStyle={{
                                  margin: '0.5em 0',
                                  borderRadius: '6px',
                                  fontSize: '0.85em',
                                }}
                                {...props}
                              >
                                {codeString}
                              </SyntaxHighlighter>
                            ) : (
                              <code className="inline-code" {...props}>
                                {children}
                              </code>
                            )
                          },
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    ) : (
                      <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {msg.content}
                      </pre>
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
                placeholder="Ask about the code..."
                className="chat-input"
                disabled={isTyping}
              />
              <button
                type="submit"
                className="chat-send-button"
                disabled={!input.trim() || isTyping}
              >
                Send
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default CodeBrowser
