import React, { useState, useRef, useEffect } from "react";
import "./ChatPanel.css";

function DemoChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = {
      type: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);

    // Simulate a demo response after a short delay
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          type: "assistant",
          content:
            "This is a demo mode. Sign in to connect to the ARES backend and get real AI responses.",
          timestamp: new Date(),
        },
      ]);
    }, 500);

    setInput("");
    inputRef.current?.focus();
  };

  const formatTime = (date) => {
    return new Date(date).toLocaleTimeString();
  };

  return (
    <div className="panel chat-panel">
      <div className="chat-header">
        <h2>Demo Chat</h2>
        <div className="demo-badge">Demo Mode</div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="empty-state">
            Try the chat interface. Sign in to connect to ARES.
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`chat-message ${msg.type}`}>
              <div className="message-header">
                <span className="message-sender">
                  {msg.type === "user" ? "You" : "ARES (Demo)"}
                </span>
                <span className="message-time">
                  {formatTime(msg.timestamp)}
                </span>
              </div>
              <div className="message-content">{msg.content}</div>
            </div>
          ))
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
            placeholder="Type a message to try the interface..."
            className="chat-input"
          />
        </div>
        <button
          type="submit"
          className="chat-send-button"
          disabled={!input.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}

export default DemoChat;
