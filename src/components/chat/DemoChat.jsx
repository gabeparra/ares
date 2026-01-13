import React, { useState, useRef, useEffect } from "react";

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
    <div className="flex flex-col flex-1 min-h-0 h-full w-full overflow-hidden box-border p-16px pb-0 gap-0 bg-transparent">
      <div className="flex justify-between items-center mb-12px pb-12px border-b border-white/10 bg-gradient-to-r from-transparent via-red/4 to-transparent px-4px -mx-4px rounded-md flex-shrink-0 flex-wrap gap-8px">
        <h2 className="m-0 flex-1 text-white/95 text-1.15em font-semibold tracking-wide">Demo Chat</h2>
        <div className="px-12px py-4px bg-yellow-500/20 border border-yellow-500/40 rounded-md text-yellow-300 text-0.85em font-semibold">Demo Mode</div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-10px pr-4px m-0 box-border">
        {messages.length === 0 ? (
          <div className="empty-state">
            Try the chat interface. Sign in to connect to ARES.
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`mb-12px px-16px py-12px rounded-xl ${
              msg.type === 'user' 
                ? 'bg-red/15 border border-red/30 text-white' 
                : 'bg-white/6 border border-white/10 text-white/95'
            }`}>
              <div className="flex justify-between items-baseline mb-6px">
                <span className="text-0.85em font-semibold text-white/90">
                  {msg.type === "user" ? "You" : "ARES (Demo)"}
                </span>
                <span className="text-0.75em text-white/40 font-mono">
                  {formatTime(msg.timestamp)}
                </span>
              </div>
              <div className="leading-normal whitespace-pre-wrap break-words text-white/90 text-1em">{msg.content}</div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-10px items-end pt-12px pb-16px flex-shrink-0">
        <div className="flex-1 min-w-0">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message to try the interface..."
            className="w-full px-16px py-12px bg-white/6 border border-white/12 rounded-xl text-white placeholder-white/40 text-1em resize-none leading-normal outline-none transition-all duration-200ms focus:border-red/50 focus:bg-white/8"
          />
        </div>
        <button
          type="submit"
          className="px-24px py-12px bg-gradient-to-br from-red/60 to-red/80 text-white font-semibold rounded-xl cursor-pointer transition-all duration-200ms border-none outline-none hover:from-red/70 hover:to-red/90 hover:shadow-[0_4px_16px_rgba(255,0,0,0.3)] disabled:opacity-40 disabled:cursor-not-allowed"
          disabled={!input.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}

export default DemoChat;
