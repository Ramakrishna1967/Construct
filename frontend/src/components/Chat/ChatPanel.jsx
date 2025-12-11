import { useState, useRef, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { Send, Sparkles, User, Bot, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function ChatPanel() {
    const { messages, sendMessage, isStreaming, connectionStatus } = useApp();
    const [input, setInput] = useState('');
    const messagesEndRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = () => {
        if (!input.trim() || isStreaming) return;
        sendMessage(input);
        setInput('');
    };

    return (
        <div className="chat-panel">
            <div className="chat-header">
                <Sparkles size={18} />
                <span>AI Assistant</span>
                <div className={`status-dot ${connectionStatus}`} style={{ marginLeft: 'auto' }} />
            </div>

            <div className="chat-messages">
                {messages.length === 0 ? (
                    <div className="chat-welcome">
                        <Sparkles size={32} style={{ color: '#7c3aed', marginBottom: 12 }} />
                        <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Welcome to Construct</div>
                        <div style={{ color: '#737373', fontSize: 13 }}>Ask me to review code, find bugs, or help with anything</div>
                    </div>
                ) : (
                    messages.map(msg => (
                        <div key={msg.id} className={`chat-message ${msg.role}`}>
                            <div className="message-avatar">
                                {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                            </div>
                            <div className="message-content">
                                {msg.sender && <div className="message-sender">{msg.sender}</div>}
                                <div className="message-text">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                                </div>
                            </div>
                        </div>
                    ))
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-wrapper">
                <textarea
                    className="chat-input"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                    placeholder="Ask AI to review your code..."
                    disabled={isStreaming || connectionStatus !== 'connected'}
                />
                <button
                    className="chat-send-btn"
                    onClick={handleSend}
                    disabled={!input.trim() || isStreaming || connectionStatus !== 'connected'}
                >
                    <Send size={18} />
                </button>
            </div>
        </div>
    );
}

export default ChatPanel;
