import { useApp } from '../../context/AppContext';
import EditorTabs from './EditorTabs';
import MonacoEditor from './MonacoEditor';
import TerminalPanel from '../Terminal/TerminalPanel';
import { Zap, Upload, MessageSquare, Terminal } from 'lucide-react';

function EditorArea({ showTerminal, onToggleTerminal }) {
    const { activeFile, openFile } = useApp();

    const handleOpenFile = () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.py,.js,.jsx,.ts,.tsx,.json,.md,.css,.html,.txt';
        input.onchange = (e) => {
            const files = Array.from(e.target.files);
            files.forEach(file => {
                const reader = new FileReader();
                reader.onload = (event) => {
                    const ext = file.name.split('.').pop()?.toLowerCase();
                    const langMap = { py: 'python', js: 'javascript', jsx: 'javascript', ts: 'typescript', json: 'json', md: 'markdown', css: 'css', html: 'html' };
                    openFile({
                        id: `file-${Date.now()}-${file.name}`,
                        name: file.name,
                        path: `/${file.name}`,
                        language: langMap[ext] || 'plaintext',
                        content: event.target.result,
                    });
                };
                reader.readAsText(file);
            });
        };
        input.click();
    };

    if (!activeFile) {
        return (
            <div className="editor-area">
                <div className="editor-welcome">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                        <div style={{ width: 48, height: 48, background: 'linear-gradient(135deg, #333 0%, #444 100%)', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Zap size={28} color="#e5e5e5" />
                        </div>
                        <div className="welcome-logo">Construct</div>
                    </div>
                    <div className="welcome-subtitle">AI-Powered Code Editor</div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: 280, marginTop: 32 }}>
                        <button className="welcome-btn" onClick={handleOpenFile}>
                            <Upload size={18} />
                            <div><div style={{ fontWeight: 500 }}>Open File</div><div style={{ fontSize: 12, color: '#737373' }}>Open files from your computer</div></div>
                        </button>
                        <button className="welcome-btn" onClick={() => document.querySelector('.chat-input')?.focus()}>
                            <MessageSquare size={18} />
                            <div><div style={{ fontWeight: 500 }}>AI Chat</div><div style={{ fontSize: 12, color: '#737373' }}>Ask AI to review or write code</div></div>
                        </button>
                        <button className="welcome-btn" onClick={onToggleTerminal}>
                            <Terminal size={18} />
                            <div><div style={{ fontWeight: 500 }}>Terminal</div><div style={{ fontSize: 12, color: '#737373' }}>Run commands</div></div>
                        </button>
                    </div>
                </div>
                {showTerminal && <TerminalPanel onClose={onToggleTerminal} />}
            </div>
        );
    }

    return (
        <div className="editor-area">
            <EditorTabs />
            <div className="editor-container">
                <MonacoEditor file={activeFile} />
            </div>
            {showTerminal && <TerminalPanel onClose={onToggleTerminal} />}
        </div>
    );
}

export default EditorArea;
