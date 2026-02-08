import { useState, useRef, useEffect } from 'react';
import { Terminal, X, Plus, Trash2 } from 'lucide-react';

function TerminalPanel({ onClose }) {
    const [output, setOutput] = useState([{ type: 'system', content: 'Construct IDE Terminal\nType "help" for commands\n' }]);
    const [input, setInput] = useState('');
    const outputRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => {
        if (outputRef.current) outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }, [output]);

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    const handleCommand = (cmd) => {
        if (!cmd.trim()) return;
        setOutput(prev => [...prev, { type: 'input', content: `$ ${cmd}` }]);
        setInput('');

        const parts = cmd.trim().split(' ');
        const base = parts[0].toLowerCase();

        switch (base) {
            case 'help':
                setOutput(prev => [...prev, { type: 'output', content: 'Commands: help, clear, version, ls, pwd, node <code>, python <code>' }]);
                break;
            case 'clear':
                setOutput([]);
                break;
            case 'version':
                setOutput(prev => [...prev, { type: 'output', content: 'Construct IDE v1.0.0' }]);
                break;
            case 'ls':
                setOutput(prev => [...prev, { type: 'output', content: '📁 src/\n📁 public/\n📄 package.json' }]);
                break;
            case 'pwd':
                setOutput(prev => [...prev, { type: 'output', content: '/workspace/construct-ide' }]);
                break;
            case 'node':
            case 'js':
                try {
                    const code = parts.slice(1).join(' ');
                    const result = eval(code);
                    setOutput(prev => [...prev, { type: 'output', content: String(result) }]);
                } catch (e) {
                    setOutput(prev => [...prev, { type: 'error', content: e.message }]);
                }
                break;
            case 'python':
                setOutput(prev => [...prev, { type: 'output', content: 'Python execution via AI - use the chat panel' }]);
                break;
            default:
                setOutput(prev => [...prev, { type: 'error', content: `Command not found: ${base}` }]);
        }
    };

    return (
        <div className="terminal-panel">
            <div className="terminal-header">
                <div className="terminal-tabs">
                    <button className="terminal-tab-btn active"><Terminal size={14} /> Terminal</button>
                </div>
                <div className="terminal-actions">
                    <button className="terminal-action-btn" onClick={() => setOutput([])}><Trash2 size={14} /></button>
                    <button className="terminal-action-btn" onClick={onClose}><X size={14} /></button>
                </div>
            </div>
            <div className="terminal-content">
                <div className="terminal-output" ref={outputRef}>
                    {output.map((line, i) => (
                        <div key={i} className={`terminal-line ${line.type}`} style={{ color: line.type === 'error' ? '#ef4444' : line.type === 'system' ? '#737373' : '#a3a3a3', whiteSpace: 'pre-wrap' }}>
                            {line.content}
                        </div>
                    ))}
                </div>
                <div className="terminal-input-line">
                    <span className="terminal-prompt">$</span>
                    <input
                        ref={inputRef}
                        type="text"
                        className="terminal-input"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleCommand(input)}
                        placeholder="Type a command..."
                    />
                </div>
            </div>
        </div>
    );
}

export default TerminalPanel;

























































































































































































































































































































































































































































































