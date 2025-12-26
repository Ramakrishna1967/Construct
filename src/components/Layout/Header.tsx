import {
    PanelLeft,
    PanelRight,
    Terminal as TerminalIcon,
    Settings,
    Github,
    Zap,
    Bot
} from 'lucide-react';
import { useStore } from '../../store/useStore';
import { CodeUpload } from '../CodeUpload';
import './Header.css';

export function Header() {
    const {
        sidebarOpen,
        aiPanelOpen,
        terminalOpen,
        toggleSidebar,
        toggleAIPanel,
        toggleTerminal,
        isConnected
    } = useStore();

    return (
        <header className="app-header">
            <div className="header-left">
                <button
                    className={`icon-btn ${sidebarOpen ? 'active' : ''}`}
                    onClick={toggleSidebar}
                    title="Toggle Sidebar"
                >
                    <PanelLeft size={18} />
                </button>

                <div className="logo">
                    <Zap size={20} className="logo-icon" />
                    <span className="logo-text">Construct</span>
                    <span className="logo-badge">AI Code Review</span>
                </div>
            </div>

            <div className="header-center">
                <CodeUpload />
                <div className="agent-status">
                    <Bot size={14} />
                    <span>5 AI Agents</span>
                    <div className={`status-dot ${isConnected ? 'online' : 'offline'}`} />
                </div>
            </div>

            <div className="header-right">
                <button
                    className={`icon-btn ${terminalOpen ? 'active' : ''}`}
                    onClick={toggleTerminal}
                    title="Toggle Output"
                >
                    <TerminalIcon size={18} />
                </button>

                <button
                    className={`icon-btn ${aiPanelOpen ? 'active' : ''}`}
                    onClick={toggleAIPanel}
                    title="Toggle AI Panel"
                >
                    <PanelRight size={18} />
                </button>

                <div className="header-divider" />

                <a
                    href="https://github.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="icon-btn"
                    title="GitHub"
                >
                    <Github size={18} />
                </a>

                <button className="icon-btn" title="Settings">
                    <Settings size={18} />
                </button>
            </div>
        </header>
    );
}
