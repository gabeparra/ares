import React, { useState, useEffect } from 'react'
import Tabs from './components/Tabs'
import TabPanel from './components/TabPanel'
import ChatPanel from './components/chat/ChatPanel'
import SegmentsPanel from './components/segments/SegmentsPanel'
import SummaryPanel from './components/segments/SummaryPanel'
import StatusIndicator from './components/controls/StatusIndicator'
import ModelSelector from './components/controls/ModelSelector'
import BackendControl from './components/controls/BackendControl'
import SummarizerControl from './components/controls/SummarizerControl'
import TelegramStatus from './components/controls/TelegramStatus'
import PowerPetDoorControl from './components/controls/PowerPetDoorControl'
import CodeBrowser from './components/code/CodeBrowser'
import ConversationList from './components/conversations/ConversationList'
import ConversationViewer from './components/conversations/ConversationViewer'
import { useWebSocket } from './services/useWebSocket'
import './styles/index.css'
import './styles/App.css'

function App() {
  const [segments, setSegments] = useState([])
  const [summary, setSummary] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [currentModel, setCurrentModel] = useState(null)
  const [activeTab, setActiveTab] = useState('chat')
  const [selectedSessionId, setSelectedSessionId] = useState(null)
  const [chatSessionId, setChatSessionId] = useState(null)
  const ws = useWebSocket()

  const tabs = [
    { id: 'chat', label: 'Chat', icon: '💬' },
    { id: 'conversations', label: 'History', icon: '📚' },
    { id: 'code', label: 'Code', icon: '📁' },
    { id: 'meetings', label: 'Meetings', icon: '🎤' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ]

  useEffect(() => {
    if (ws) {
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        
        if (data.type === 'segment') {
          setSegments(prev => [data.segment, ...prev])
        } else if (data.type === 'summary') {
          setSummary(data.summary)
        } else if (data.type === 'init') {
          if (data.segments) {
            setSegments(data.segments)
          }
          if (data.summary) {
            setSummary(data.summary)
          }
          if (data.current_model) {
            setCurrentModel(data.current_model)
          }
        } else if (data.type === 'chat_response') {
          // Handle chat response - will be added to chat component
        } else if (data.type === 'model_changed') {
          setCurrentModel(data.model)
        }
      }

      ws.onopen = () => {
        setIsConnected(true)
        ws.send(JSON.stringify({ type: 'init' }))
      }

      ws.onclose = () => {
        setIsConnected(false)
      }

      ws.onerror = () => {
        setIsConnected(false)
      }
    }

    return () => {
      if (ws) {
        ws.close()
      }
    }
  }, [ws])

  const handleBackendRefresh = () => {
    if (ws) {
      ws.close()
    }
    window.location.reload()
  }

  const handleContinueConversation = (sessionId) => {
    setChatSessionId(sessionId)
    setActiveTab('chat')
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="title-section">
            <h1>GLUP</h1>
            <div className="subtitle">Advanced Meeting Intelligence | Neural Processing Active</div>
          </div>
          <StatusIndicator connected={isConnected} />
        </div>
      </header>
      
      <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab}>
        <TabPanel id="chat" active={activeTab === 'chat'}>
          <div className="chat-layout">
            <div className="chat-main">
              <ChatPanel
                ws={ws}
                sessionId={chatSessionId}
                onSessionChange={setChatSessionId}
              />
            </div>
            <div className="chat-sidebar">
              <BackendControl isConnected={isConnected} onRefresh={handleBackendRefresh} />
              <TelegramStatus />
              <SummarizerControl ws={ws} />
              <PowerPetDoorControl />
            </div>
          </div>
        </TabPanel>

        <TabPanel id="conversations" active={activeTab === 'conversations'}>
          <div className="conversations-layout">
            <div className="conversations-sidebar">
              <ConversationList 
                onSelectSession={setSelectedSessionId}
                selectedSessionId={selectedSessionId}
              />
            </div>
            <div className="conversations-main">
              <ConversationViewer
                sessionId={selectedSessionId}
                onContinueConversation={handleContinueConversation}
              />
            </div>
          </div>
        </TabPanel>

        <TabPanel id="code" active={activeTab === 'code'}>
          <CodeBrowser />
        </TabPanel>

        <TabPanel id="meetings" active={activeTab === 'meetings'}>
          <div className="meetings-layout">
            <div className="meetings-main">
              <SegmentsPanel segments={segments} />
            </div>
            <div className="meetings-sidebar">
              <SummaryPanel summary={summary} />
            </div>
          </div>
        </TabPanel>

        <TabPanel id="settings" active={activeTab === 'settings'}>
          <div className="settings-layout">
            <ModelSelector currentModel={currentModel} onModelChange={setCurrentModel} />
          </div>
        </TabPanel>
      </Tabs>
      
      <footer className="app-footer">
        <div className="footer-content">
          <span className="footer-text">Gabriel Parra</span>
          <span className="footer-separator">|</span>
          <span className="footer-text">© 2025</span>
        </div>
      </footer>
    </div>
  )
}

export default App
