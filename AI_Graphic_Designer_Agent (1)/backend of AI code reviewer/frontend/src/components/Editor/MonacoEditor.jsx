import Editor from '@monaco-editor/react';

function MonacoEditor({ file }) {
    const getLanguage = (lang) => {
        const langMap = { python: 'python', javascript: 'javascript', typescript: 'typescript', json: 'json', markdown: 'markdown', css: 'css', html: 'html' };
        return langMap[lang] || 'plaintext';
    };

    const handleEditorMount = (editor, monaco) => {
        monaco.editor.defineTheme('constructTheme', {
            base: 'vs-dark',
            inherit: true,
            rules: [
                { token: 'comment', foreground: '525252', fontStyle: 'italic' },
                { token: 'keyword', foreground: 'c084fc' },
                { token: 'string', foreground: '4ade80' },
                { token: 'number', foreground: 'fb923c' },
                { token: 'function', foreground: '60a5fa' },
            ],
            colors: {
                'editor.background': '#000000',
                'editor.foreground': '#e5e5e5',
                'editorLineNumber.foreground': '#404040',
                'editorLineNumber.activeForeground': '#737373',
                'editor.selectionBackground': '#262626',
                'editor.lineHighlightBackground': '#0a0a0a',
                'editorCursor.foreground': '#7c3aed',
            },
        });
        monaco.editor.setTheme('constructTheme');
    };

    return (
        <Editor
            height="100%"
            language={getLanguage(file?.language)}
            value={file?.content || ''}
            theme="vs-dark"
            onMount={handleEditorMount}
            options={{
                fontSize: 14,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                minimap: { enabled: true, maxColumn: 80 },
                scrollBeyondLastLine: false,
                lineNumbers: 'on',
                renderLineHighlight: 'all',
                cursorBlinking: 'smooth',
                smoothScrolling: true,
                padding: { top: 16 },
            }}
        />
    );
}

export default MonacoEditor;
