import Editor from '@monaco-editor/react';
import { X, Circle, Play, Loader2 } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { executeCode, getLanguageFromFile } from '../../services/codeExecution';
import './EditorPanel.css';

export function EditorPanel() {
    const {
        files,
        activeTab,
        setActiveTab,
        closeFile,
        updateFile,
        isExecuting,
        setExecuting,
        addTerminalOutput,
        terminalOpen,
        toggleTerminal
    } = useStore();

    const activeFile = files.find((f) => f.id === activeTab);

    const getLanguage = (lang: string) => {
        const langMap: Record<string, string> = {
            typescript: 'typescript',
            javascript: 'javascript',
            python: 'python',
            json: 'json',
            markdown: 'markdown',
            html: 'html',
            css: 'css',
            java: 'java',
            cpp: 'cpp',
            c: 'c',
            csharp: 'csharp',
            go: 'go',
            rust: 'rust',
            ruby: 'ruby',
            php: 'php',
        };
        return langMap[lang] || 'plaintext';
    };

    const handleRunCode = async () => {
        if (!activeFile || isExecuting) return;

        const language = getLanguageFromFile(activeFile.name);

        // Open terminal if closed
        if (!terminalOpen) {
            toggleTerminal();
        }

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

    const canRun = activeFile &&
        !activeFile.name.endsWith('.md') &&
        !activeFile.name.endsWith('.json') &&
        !activeFile.name.endsWith('.css') &&
        !activeFile.name.endsWith('.html');

    return (
        <div className="editor-panel">
            {/* Tab Bar */}
            <div className="tab-bar">
                <div className="tabs">
                    {files.map((file) => (
                        <div
                            key={file.id}
                            className={`tab ${activeTab === file.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(file.id)}
                        >
                            <span className="tab-name">{file.name}</span>
                            {file.isModified && (
                                <Circle size={8} className="tab-modified" fill="currentColor" />
                            )}
                            <button
                                className="tab-close"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    closeFile(file.id);
                                }}
                            >
                                <X size={14} />
                            </button>
                        </div>
                    ))}
                </div>

                {/* Run Button in Tab Bar */}
                {canRun && (
                    <button
                        className={`editor-run-btn ${isExecuting ? 'running' : ''}`}
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
                                <span>Run</span>
                            </>
                        )}
                    </button>
                )}
            </div>

            {/* Editor */}
            <div className="editor-container">
                {activeFile ? (
                    <Editor
                        height="100%"
                        language={getLanguage(activeFile.language)}
                        value={activeFile.content}
                        onChange={(value) => updateFile(activeFile.id, value || '')}
                        theme="vs-dark"
                        options={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 13,
                            lineHeight: 20,
                            minimap: { enabled: true, scale: 1 },
                            scrollBeyondLastLine: false,
                            renderLineHighlight: 'all',
                            cursorBlinking: 'smooth',
                            cursorSmoothCaretAnimation: 'on',
                            smoothScrolling: true,
                            padding: { top: 16, bottom: 16 },
                            automaticLayout: true,
                            wordWrap: 'on',
                            bracketPairColorization: { enabled: true },
                            folding: true,
                            foldingStrategy: 'indentation',
                            showFoldingControls: 'mouseover',
                            glyphMargin: true,
                            lineNumbers: 'on',
                            lineDecorationsWidth: 10,
                            renderWhitespace: 'selection',
                        }}
                    />
                ) : (
                    <div className="no-file">
                        <div className="no-file-content">
                            <h2>Construct IDE</h2>
                            <p>Select a file to start editing</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
