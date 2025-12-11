import { useApp } from '../../context/AppContext';
import { X, FileCode } from 'lucide-react';

function EditorTabs() {
    const { openFiles, activeFile, openFile, closeFile } = useApp();

    if (openFiles.length === 0) return null;

    return (
        <div className="editor-tabs">
            {openFiles.map(file => (
                <div
                    key={file.id}
                    className={`editor-tab ${activeFile?.id === file.id ? 'active' : ''}`}
                    onClick={() => openFile(file)}
                >
                    <FileCode size={14} />
                    <span>{file.name}</span>
                    <button
                        className="tab-close"
                        onClick={(e) => { e.stopPropagation(); closeFile(file.id); }}
                    >
                        <X size={14} />
                    </button>
                </div>
            ))}
        </div>
    );
}

export default EditorTabs;
