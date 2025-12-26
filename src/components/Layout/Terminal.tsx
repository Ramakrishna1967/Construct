import { useRef, useEffect, useState } from 'react';
import {
    X,
    TerminalSquare,
    Play,
    Trash2,
    Loader2,
    CheckCircle2,
    XCircle,
    Clock,
    Maximize2,
    Minimize2
} from 'lucide-react';
import { useStore } from '../../store/useStore';
import { executeCode, getLanguageFromFile } from '../../services/codeExecution';
import './Terminal.css';

export function Terminal() {
    const [isMaximized, setIsMaximized] = useState(false);
    const {
        terminalOpen,
        toggleTerminal,
        terminalOutput,
        addTerminalOutput,
        clearTerminal,
        isExecuting,
        setExecuting,
        files,
        activeTab
    } = useStore();

    const outputRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        if (outputRef.current) {
            outputRef.current.scrollTop = outputRef.current.scrollHeight;
        }
    }, [terminalOutput]);

    const handleRunCode = async () => {
        const activeFile = files.find((f) => f.id === activeTab);
        if (!activeFile || isExecuting) return;

        const language = getLanguageFromFile(activeFile.name);

        // Add command to terminal
        addTerminalOutput({
            type: 'command',
            content: `$ Running ${activeFile.name}...`,
        });

        setExecuting(true);

        try {
            const result = await executeCode(activeFile.content, language);

            if (result.success) {
                addTerminalOutput({
                    type: 'output',
                    content: result.output,
                });
                addTerminalOutput({
                    type: 'info',
                    content: `✓ Completed in ${result.runtime} (${result.language})`,
                });
            } else {
                if (result.output) {
                    addTerminalOutput({
                        type: 'output',
                        content: result.output,
                    });
                }
                addTerminalOutput({
                    type: 'error',
                    content: `✗ Error: ${result.error}`,
                });
            }
        } catch (error) {
            addTerminalOutput({
                type: 'error',
                content: `✗ Execution failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
            });
        } finally {
            setExecuting(false);
            addTerminalOutput({
                type: 'info',
                content: '',
            });
        }
    };

    // Keyboard shortcut: Ctrl+Enter to run
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                handleRunCode();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [files, activeTab, isExecuting]);

    if (!terminalOpen) return null;

    const activeFile = files.find((f) => f.id === activeTab);
    const canRun = activeFile &&
        !activeFile.name.endsWith('.md') &&
        !activeFile.name.endsWith('.json') &&
        !activeFile.name.endsWith('.css') &&
        !activeFile.name.endsWith('.html');

    return (
        <div className={`terminal-panel ${isMaximized ? 'maximized' : ''}`}>
            <div className="terminal-header">
                <div className="terminal-tabs">
                    <div className="terminal-tab active">
                        <TerminalSquare size={14} />
                        <span>COMPILER OUTPUT</span>
                    </div>
                </div>

                <div className="terminal-actions">
                    {canRun && (
                        <button
                            className={`run-btn ${isExecuting ? 'running' : ''}`}
                            onClick={handleRunCode}
                            disabled={isExecuting}
                            title="Run Code (Ctrl+Enter)"
                        >
                            {isExecuting ? (
                                <>
                                    <Loader2 size={14} className="spin" />
                                    <span>Running...</span>
                                </>
                            ) : (
                                <>
                                    <Play size={14} />
                                    <span>Run Code</span>
                                </>
                            )}
                        </button>
                    )}

                    <button
                        className="icon-btn"
                        onClick={clearTerminal}
                        title="Clear Output"
                    >
                        <Trash2 size={14} />
                    </button>

                    <button
                        className="icon-btn"
                        onClick={() => setIsMaximized(!isMaximized)}
                        title={isMaximized ? "Minimize" : "Maximize"}
                    >
                        {isMaximized ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                    </button>

                    <button className="icon-btn" onClick={toggleTerminal} title="Close">
                        <X size={14} />
                    </button>
                </div>
            </div>

            <div className="terminal-content" ref={outputRef}>
                {terminalOutput.length === 0 ? (
                    <div className="terminal-empty">
                        <TerminalSquare size={24} />
                        <p>Click "Run Code" to execute your code</p>
                        <span>Supports Python, JavaScript, Java, C++, Go, Rust, and more</span>
                    </div>
                ) : (
                    terminalOutput.map((line) => (
                        <div
                            key={line.id}
                            className={`terminal-line ${line.type}`}
                        >
                            {line.type === 'command' && <span className="prompt">›</span>}
                            {line.type === 'output' && <CheckCircle2 size={12} className="line-icon success" />}
                            {line.type === 'error' && <XCircle size={12} className="line-icon error" />}
                            {line.type === 'info' && line.content.includes('Completed') && <Clock size={12} className="line-icon info" />}
                            <pre className="line-content">{line.content}</pre>
                        </div>
                    ))
                )}

                {isExecuting && (
                    <div className="terminal-line executing">
                        <Loader2 size={12} className="spin" />
                        <span>Executing code...</span>
                    </div>
                )}
            </div>
        </div>
    );
}
