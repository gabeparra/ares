import React, { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { getAuthToken } from '../../services/auth'

function CodeBrowser() {
  const [files, setFiles] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileContent, setFileContent] = useState(null)
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [textWrap, setTextWrap] = useState(false)
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
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
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
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
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
      const token = getAuthToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
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
    <div className="panel flex flex-col h-full min-h-0 overflow-hidden p-2 px-3 box-border relative">
      <div className="flex justify-between items-center mb-2 flex-wrap gap-2 flex-shrink-0 p-0">
        <h2 className="m-0 text-1em font-600 bg-gradient-to-br from-white to-red-accent bg-clip-text text-transparent">Code Browser</h2>
      </div>

      <div className="flex flex-1 min-h-0 gap-3 overflow-hidden mt-0 w-full box-border items-stretch">
        {/* File Browser Sidebar */}
        <div className="flex-[0_1_280px] min-w-[220px] max-w-[350px] flex flex-col min-h-0 overflow-hidden bg-black bg-opacity-20 rounded-xl p-3 box-border relative">
          <div className="mb-3 flex-shrink-0 w-full box-border min-w-0">
            <input
              type="text"
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="w-full max-w-full px-3 py-2.5 bg-white-opacity-10 border border-white-opacity-20 rounded-lg text-white text-0.9em box-border min-w-0 placeholder-white-opacity-50"
            />
          </div>

          <div className="flex-1 overflow-y-auto overflow-x-hidden min-h-0 w-full box-border min-w-0">
            {loading && !fileContent && <div className="flex items-center justify-center py-5 text-white-opacity-70 text-0.9em">Loading files...</div>}
            {Object.keys(groupedFiles).map(dir => (
              <div key={dir} className="mb-3">
                {dir !== '/' && (
                  <div className="px-2.5 py-2.5 font-600 text-0.8em text-white-opacity-70 mb-1.5">
                    📁 {dir}
                  </div>
                )}
                {groupedFiles[dir].map((file) => (
                  <div
                    key={file.path}
                    className={`flex items-center gap-1.5 px-2.5 py-2.5 cursor-pointer transition-all duration-200 rounded text-0.85em w-full box-border min-w-0 max-w-full hover:bg-white-opacity-6 ${
                      selectedFile === file.path ? 'bg-red-bg-4 text-white' : ''
                    }`}
                    onClick={() => handleFileSelect(file.path)}
                    title={file.path}
                  >
                    <span className="text-1em flex-shrink-0">
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
                    <span className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap">{file.name}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Code Viewer */}
        <div className="flex-[2] min-w-0 flex flex-col min-h-0 overflow-hidden bg-black bg-opacity-30 rounded-lg p-3 box-border relative">
          {loading && fileContent === null && (
            <div className="flex items-center justify-center py-5 text-white-opacity-70 text-0.9em">Loading file...</div>
          )}
          
          {fileContent && (
            <div className="flex flex-col h-full min-h-0 w-full box-border overflow-hidden relative flex-1">
              <div className="flex justify-between items-center mb-3 flex-shrink-0 gap-2">
                <span className="font-mono text-0.8em text-white-opacity-80 overflow-hidden text-ellipsis whitespace-nowrap flex-1 min-w-0">{fileContent.file_path}</span>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={() => setTextWrap(!textWrap)}
                    className={`px-3 py-1.5 bg-white-opacity-10 border border-white-opacity-20 rounded text-white cursor-pointer text-0.8em transition-all duration-200 flex-shrink-0 whitespace-nowrap hover:bg-white-opacity-15 hover:border-white-opacity-30 ${
                      textWrap ? 'bg-white-opacity-20 border-white-opacity-40' : ''
                    }`}
                    title={textWrap ? 'Disable text wrap' : 'Enable text wrap'}
                  >
                    {textWrap ? '🔤 Wrap' : '📄 No Wrap'}
                  </button>
                  <button
                    onClick={() => sendFileToChat(fileContent.file_path, fileContent)}
                    className="px-3 py-1.5 bg-white-opacity-10 border border-white-opacity-20 rounded text-white cursor-pointer text-0.8em transition-all duration-200 flex-shrink-0 whitespace-nowrap hover:bg-white-opacity-15 hover:border-white-opacity-30"
                    title="Send file to chat for review"
                  >
                    💬 Review in Chat
                  </button>
                </div>
              </div>
              <div className={`flex-1 overflow-x-auto overflow-y-auto min-h-0 m-0 w-full box-border relative ${textWrap ? 'overflow-x-hidden pr-4' : ''}`} style={{ background: 'rgb(40, 44, 52)' }}>
                <div className="flex w-full relative" style={{ background: 'rgb(40, 44, 52)', minHeight: '100%' }}>
                  <div className="flex-shrink-0 py-3 px-2 pl-3 bg-black bg-opacity-30 border-r border-white-opacity-10 select-none font-mono text-0.85em text-white-opacity-40 text-right leading-[1.5] min-w-[50px] box-border">
                    {fileContent.content.split('\n').map((_, index) => (
                      <div key={index} className="p-0 m-0 min-h-[1.5em] block whitespace-nowrap">
                        {index + 1}
                      </div>
                    ))}
                  </div>
                  <div className="flex-1 min-w-0 overflow-visible" style={{ background: 'rgb(40, 44, 52)' }}>
                    <SyntaxHighlighter
                      style={oneDark}
                      language={fileContent.language || 'text'}
                      PreTag="div"
                      customStyle={{
                        margin: 0,
                        borderRadius: 0,
                        fontSize: '0.85em',
                        padding: '12px',
                        overflow: 'visible',
                        whiteSpace: textWrap ? 'pre-wrap' : 'pre',
                        wordWrap: textWrap ? 'break-word' : 'normal',
                        wordBreak: textWrap ? 'break-word' : 'normal',
                        overflowWrap: textWrap ? 'break-word' : 'normal',
                        lineHeight: '1.5',
                      }}
                    >
                      {fileContent.content}
                    </SyntaxHighlighter>
                  </div>
                </div>
              </div>
            </div>
          )}

          {!fileContent && !loading && (
            <div className="flex items-center justify-center flex-1 min-h-[200px] text-white-opacity-75 text-0.95em text-center py-6 px-6 rounded-2xl bg-white-opacity-5 border border-white-opacity-15 shadow-[0_4px_12px_rgba(0,0,0,0.3),inset_0_1px_0_rgba(255,255,255,0.1)] w-full max-w-full box-border overflow-hidden break-words overflow-wrap-break-word m-0">
              Select a file to view its contents
            </div>
          )}
        </div>

        {/* Chat Panel */}
        <div className="flex-[0_1_360px] min-w-[280px] max-w-[450px] flex flex-col min-h-0 h-full overflow-hidden bg-black bg-opacity-30 border border-white-opacity-10 rounded-lg p-3 self-stretch box-border relative shadow-[0_2px_8px_rgba(0,0,0,0.2)]">
          <div className="flex justify-between items-center mb-3 flex-shrink-0 gap-2 px-3 py-2 rounded-lg bg-white-opacity-5">
            <h3 className="m-0 text-1em font-600 text-white flex-1">Ask about Code</h3>
            <button onClick={loadFiles} className="bg-white-opacity-10 border border-white-opacity-20 rounded-xl px-3 py-2 cursor-pointer text-white text-0.9em transition-all duration-200 flex-shrink-0 hover:bg-white-opacity-15 hover:border-white-opacity-30" title="Refresh file list">
              🔄
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto overflow-x-hidden min-h-0 mb-2 px-3 py-3 rounded-xl bg-black bg-opacity-25 border border-white-opacity-8 w-full box-border min-w-0 flex flex-col">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center flex-1 min-h-[200px] text-white-opacity-75 text-0.95em text-center py-6 px-6 rounded-2xl bg-white-opacity-5 border border-white-opacity-15 shadow-[0_4px_12px_rgba(0,0,0,0.3),inset_0_1px_0_rgba(255,255,255,0.1)] w-full max-w-full box-border overflow-hidden break-words overflow-wrap-break-word m-0">
                Select a file and ask questions about it...
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`mb-3 px-2.5 py-2.5 rounded ${
                  msg.type === 'user' ? 'bg-white-opacity-10' : 
                  msg.type === 'error' ? 'bg-red-bg-3' : 
                  'bg-[rgba(0,255,0,0.05)]'
                }`}>
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-600 text-0.85em text-white-opacity-90">
                      {msg.type === 'user' ? 'You' : msg.type === 'error' ? 'Error' : 'ARES'}
                    </span>
                    <span className="text-0.75em text-white-opacity-50">{formatTime(msg.timestamp)}</span>
                  </div>
                  <div className="text-white-opacity-90 text-0.85em leading-[1.4]">
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
                              <code className="bg-black bg-opacity-30 px-1.5 py-0.5 rounded font-mono text-0.9em" {...props}>
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
              <div className="mb-3 px-2.5 py-2.5 rounded bg-[rgba(0,255,0,0.05)]">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-600 text-0.85em text-white-opacity-90">ARES</span>
                </div>
                <div className="flex gap-1 py-2">
                  <span className="w-2 h-2 rounded-full bg-white-opacity-50 animate-typing"></span>
                  <span className="w-2 h-2 rounded-full bg-white-opacity-50 animate-typing" style={{ animationDelay: '0.2s' }}></span>
                  <span className="w-2 h-2 rounded-full bg-white-opacity-50 animate-typing" style={{ animationDelay: '0.4s' }}></span>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSubmit} className="flex-shrink-0 p-0 m-0 w-full box-border min-w-0">
            <div className="flex gap-2 w-full box-border min-w-0">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about the code..."
                className="flex-1 min-w-0 max-w-full px-3 py-2.5 bg-white-opacity-10 border border-white-opacity-20 rounded-xl text-white text-0.85em box-border placeholder-white-opacity-50"
                disabled={isTyping}
              />
              <button
                type="submit"
                className="px-5 py-2.5 bg-white-opacity-10 border border-white-opacity-20 rounded-xl text-white cursor-pointer text-0.85em transition-all duration-200 flex-shrink-0 hover:bg-white-opacity-15 hover:border-white-opacity-30 disabled:opacity-50 disabled:cursor-not-allowed"
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
