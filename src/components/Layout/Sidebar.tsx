import {
    FolderOpen,
    FileCode2,
    FileJson,
    FileText,
    FileType,
    ChevronDown,
    Plus,
    Trash2,
    File
} from 'lucide-react';
import { useState } from 'react';
import { useStore } from '../../store/useStore';
import './Sidebar.css';

const getFileIcon = (name: string) => {
    if (name.endsWith('.tsx') || name.endsWith('.ts')) {
        return <FileCode2 size={16} className="file-icon ts" />;
    }
    if (name.endsWith('.json')) {
        return <FileJson size={16} className="file-icon json" />;
    }
    if (name.endsWith('.md')) {
        return <FileText size={16} className="file-icon md" />;
    }
    if (name.endsWith('.py')) {
        return <FileCode2 size={16} className="file-icon py" />;
    }
    if (name.endsWith('.js') || name.endsWith('.jsx')) {
        return <FileCode2 size={16} className="file-icon js" />;
    }
    return <FileType size={16} className="file-icon" />;
};

export function Sidebar() {
    const { sidebarOpen, files, activeTab, setActiveTab, addFile, closeFile } = useStore();
    const [isCreating, setIsCreating] = useState(false);
    const [newFileName, setNewFileName] = useState('');
    const [hoveredFile, setHoveredFile] = useState<string | null>(null);

    const getLanguageFromExtension = (name: string): string => {
        if (name.endsWith('.tsx') || name.endsWith('.ts')) return 'typescript';
        if (name.endsWith('.jsx') || name.endsWith('.js')) return 'javascript';
        if (name.endsWith('.py')) return 'python';
        if (name.endsWith('.json')) return 'json';
        if (name.endsWith('.md')) return 'markdown';
        if (name.endsWith('.html')) return 'html';
        if (name.endsWith('.css')) return 'css';
        return 'plaintext';
    };

    const getDefaultContent = (name: string): string => {
        if (name.endsWith('.tsx') || name.endsWith('.jsx')) {
            return `// ${name}\nimport React from 'react';\n\nexport function Component() {\n  return (\n    <div>\n      <h1>Hello World</h1>\n    </div>\n  );\n}\n`;
        }
        if (name.endsWith('.ts') || name.endsWith('.js')) {
            return `// ${name}\n\nexport function example() {\n  console.log("Hello, World!");\n}\n`;
        }
        if (name.endsWith('.py')) {
            return `# ${name}\n\ndef main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()\n`;
        }
        if (name.endsWith('.json')) {
            return `{\n  "name": "${name.replace('.json', '')}",\n  "version": "1.0.0"\n}\n`;
        }
        if (name.endsWith('.md')) {
            return `# ${name.replace('.md', '')}\n\nWrite your documentation here.\n`;
        }
        return `// ${name}\n`;
    };

    const handleCreateFile = () => {
        if (!newFileName.trim()) {
            setIsCreating(false);
            return;
        }

        const fileName = newFileName.includes('.') ? newFileName : `${newFileName}.ts`;
        const language = getLanguageFromExtension(fileName);

        addFile({
            id: `file-${Date.now()}`,
            name: fileName,
            path: `/${fileName}`,
            content: getDefaultContent(fileName),
            language,
            isModified: false,
        });

        setNewFileName('');
        setIsCreating(false);
    };

    const handleDeleteFile = (e: React.MouseEvent, fileId: string) => {
        e.stopPropagation();
        closeFile(fileId);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleCreateFile();
        } else if (e.key === 'Escape') {
            setIsCreating(false);
            setNewFileName('');
        }
    };

    if (!sidebarOpen) return null;

    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <span className="sidebar-title">EXPLORER</span>
                <div className="sidebar-actions">
                    <button
                        className="icon-btn"
                        title="New File"
                        onClick={() => setIsCreating(true)}
                    >
                        <Plus size={16} />
                    </button>
                </div>
            </div>

            <div className="sidebar-section">
                <div className="section-header">
                    <ChevronDown size={14} />
                    <span>YOUR FILES</span>
                </div>

                <div className="file-tree">
                    {/* New File Input */}
                    {isCreating && (
                        <div className="file-item creating">
                            <File size={16} className="file-icon" />
                            <input
                                type="text"
                                className="new-file-input"
                                placeholder="filename.ts"
                                value={newFileName}
                                onChange={(e) => setNewFileName(e.target.value)}
                                onKeyDown={handleKeyDown}
                                onBlur={handleCreateFile}
                                autoFocus
                            />
                        </div>
                    )}

                    {/* File List */}
                    {files.map((file) => (
                        <div
                            key={file.id}
                            className={`file-item ${activeTab === file.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(file.id)}
                            onMouseEnter={() => setHoveredFile(file.id)}
                            onMouseLeave={() => setHoveredFile(null)}
                        >
                            {getFileIcon(file.name)}
                            <span className="file-name">{file.name}</span>
                            {file.isModified && <span className="file-modified">●</span>}
                            {hoveredFile === file.id && files.length > 1 && (
                                <button
                                    className="file-delete"
                                    onClick={(e) => handleDeleteFile(e, file.id)}
                                    title="Delete file"
                                >
                                    <Trash2 size={14} />
                                </button>
                            )}
                        </div>
                    ))}

                    {files.length === 0 && !isCreating && (
                        <div className="empty-state">
                            <FolderOpen size={24} />
                            <p>No files yet</p>
                            <button onClick={() => setIsCreating(true)}>
                                <Plus size={14} />
                                Create a file
                            </button>
                        </div>
                    )}
                </div>
            </div>

            <div className="sidebar-footer">
                <div className="storage-info">
                    <div className="storage-bar">
                        <div
                            className="storage-used"
                            style={{ width: `${Math.min(files.length * 10, 100)}%` }}
                        />
                    </div>
                    <span className="storage-text">{files.length} file{files.length !== 1 ? 's' : ''}</span>
                </div>
            </div>
        </aside>
    );
}
