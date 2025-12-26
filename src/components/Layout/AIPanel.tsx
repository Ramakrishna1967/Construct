import { useState, useRef, useEffect } from 'react';
import {
    Bot,
    Send,
    Sparkles,
    Code2,
    AlertTriangle,
    CheckCircle2,
    Info,
    Lightbulb,
    Loader2,
    Wifi,
    WifiOff,
    User,
    ThumbsUp,
    ThumbsDown,
    Flag
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore, Message } from '../../store/useStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import './AIPanel.css';

const agentIcons: Record<string, React.ReactNode> = {
    supervisor: <Sparkles size={14} />,
    planner: <Lightbulb size={14} />,
    researcher: <Info size={14} />,
    coder: <Code2 size={14} />,
    reviewer: <CheckCircle2 size={14} />,
};

const agentColors: Record<string, string> = {
    supervisor: '#8b5cf6',
    planner: '#f59e0b',
    researcher: '#3b82f6',
    coder: '#22c55e',
    reviewer: '#ec4899',
};

function ChatMessage({ message }: { message: Message }) {
    const isUser = message.role === 'user';
    const isSystem = message.role === 'system';
    const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

    const handleFeedback = (type: 'up' | 'down') => {
        setFeedback(type);
        // In a real startup, this would send data to your research database
        console.log(`Research Data: Agent Loophole Feedback - [${message.agent}] ${type}`, {
            content: message.content,
            timestamp: new Date()
        });
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`chat-message ${isUser ? 'user' : 'assistant'} ${isSystem ? 'system' : ''}`}
        >
            <div className="message-avatar">
                {isUser ? (
                    <User size={16} />
                ) : (
                    <Bot size={16} />
                )}
            </div>

            <div className="message-content">
                {message.agent && (
                    <div
                        className="message-agent"
                        style={{ color: agentColors[message.agent] || 'var(--accent)' }}
                    >
                        {agentIcons[message.agent]}
                        <span>{message.agent}</span>
                    </div>
                )}

                <div className={`message-text ${message.isStreaming ? 'typing-cursor' : ''}`}>
                    {message.content || (message.isStreaming && '...')}
                </div>

                <div className="message-footer">
                    {!isUser && !isSystem && !message.isStreaming && (
                        <div className="message-research-actions">
                            <button
                                className={`feedback-btn ${feedback === 'up' ? 'active-up' : ''}`}
                                onClick={() => handleFeedback('up')}
                                title="Accurate Response"
                            >
                                <ThumbsUp size={12} />
                            </button>
                            <button
                                className={`feedback-btn ${feedback === 'down' ? 'active-down' : ''}`}
                                onClick={() => handleFeedback('down')}
                                title="Identify Loophole (Inaccurate)"
                            >
                                <ThumbsDown size={12} />
                            </button>
                            <button
                                className="report-loophole-btn"
                                onClick={() => alert("Research: Specific loophole details recorded for analysis.")}
                                title="Detailed Loophole Report"
                            >
                                <Flag size={12} />
                                <span>Found Loophole</span>
                            </button>
                        </div>
                    )}

                    <div className="message-time">
                        {message.timestamp.toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit'
                        })}
                    </div>
                </div>
            </div>
        </motion.div>
    );
}

function SuggestionCard({ suggestion }: { suggestion: { type: string; line: number; message: string; agent: string } }) {
    const iconMap = {
        error: <AlertTriangle size={14} />,
        warning: <AlertTriangle size={14} />,
        info: <Info size={14} />,
        improvement: <Lightbulb size={14} />,
    };

    return (
        <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className={`suggestion-card ${suggestion.type}`}
        >
            <div className="suggestion-icon">
                {iconMap[suggestion.type as keyof typeof iconMap] || <Info size={14} />}
            </div>
            <div className="suggestion-content">
                <div className="suggestion-header">
                    <span className="suggestion-line">Line {suggestion.line}</span>
                    <span className="suggestion-agent">{suggestion.agent}</span>
                </div>
                <p className="suggestion-message">{suggestion.message}</p>
            </div>
        </motion.div>
    );
}

export function AIPanel() {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    const {
        aiPanelOpen,
        messages,
        suggestions,
        isProcessing,
        files,
        activeTab
    } = useStore();

    const { connect, sendMessage, isConnected, isConnecting } = useWebSocket();

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Connect on mount
    useEffect(() => {
        connect();
    }, [connect]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isProcessing) return;

        // Get current code from active file
        const activeFile = files.find((f) => f.id === activeTab);
        const code = activeFile?.content;

        sendMessage(input, code);
        setInput('');
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    const handleQuickAction = (action: string) => {
        const activeFile = files.find((f) => f.id === activeTab);
        if (!activeFile) return;

        const prompts: Record<string, string> = {
            review: 'Please review this code for bugs, security issues, and best practices.',
            optimize: 'Suggest optimizations to improve performance and efficiency.',
            explain: 'Explain what this code does step by step.',
            security: 'Perform a security audit on this code.',
        };

        sendMessage(prompts[action] || action, activeFile.content);
    };

    if (!aiPanelOpen) return null;

    return (
        <aside className="ai-panel">
            {/* Header */}
            <div className="ai-header">
                <div className="ai-title">
                    <Bot size={18} />
                    <span>AI Assistant</span>
                </div>
                <div className={`connection-status ${isConnected ? 'connected' : ''}`}>
                    {isConnecting ? (
                        <Loader2 size={14} className="spin" />
                    ) : isConnected ? (
                        <Wifi size={14} />
                    ) : (
                        <WifiOff size={14} />
                    )}
                    <span>{isConnecting ? 'Connecting' : isConnected ? 'Connected' : 'Offline'}</span>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="quick-actions">
                <button onClick={() => handleQuickAction('review')} disabled={isProcessing}>
                    <CheckCircle2 size={14} />
                    Review
                </button>
                <button onClick={() => handleQuickAction('optimize')} disabled={isProcessing}>
                    <Sparkles size={14} />
                    Optimize
                </button>
                <button onClick={() => handleQuickAction('explain')} disabled={isProcessing}>
                    <Info size={14} />
                    Explain
                </button>
                <button onClick={() => handleQuickAction('security')} disabled={isProcessing}>
                    <AlertTriangle size={14} />
                    Security
                </button>
            </div>

            {/* Suggestions */}
            <AnimatePresence>
                {suggestions.length > 0 && (
                    <motion.div
                        className="suggestions-section"
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                    >
                        <div className="suggestions-header">
                            <Lightbulb size={14} />
                            <span>Suggestions ({suggestions.length})</span>
                        </div>
                        <div className="suggestions-list">
                            {suggestions.slice(0, 5).map((s) => (
                                <SuggestionCard key={s.id} suggestion={s} />
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Messages */}
            <div className="messages-container">
                {messages.map((msg) => (
                    <ChatMessage key={msg.id} message={msg} />
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form className="ai-input-form" onSubmit={handleSubmit}>
                <div className="input-wrapper">
                    <textarea
                        ref={inputRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask AI to review your code..."
                        rows={2}
                        disabled={isProcessing || !isConnected}
                    />
                    <button
                        type="submit"
                        className="send-btn"
                        disabled={!input.trim() || isProcessing || !isConnected}
                    >
                        {isProcessing ? (
                            <Loader2 size={18} className="spin" />
                        ) : (
                            <Send size={18} />
                        )}
                    </button>
                </div>
                <div className="input-hint">
                    Press <kbd>Enter</kbd> to send, <kbd>Shift + Enter</kbd> for new line
                </div>
            </form>
        </aside>
    );
}
