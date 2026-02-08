import { useApp } from '../../context/AppContext';
import { FolderOpen, Upload } from 'lucide-react';

function FileExplorer() {
    const { openFile } = useApp();

    const handleOpenFile = () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.py,.js,.jsx,.ts,.tsx,.json,.md,.css,.html,.txt';
        input.multiple = true;

        input.onchange = (e) => {
            const files = Array.from(e.target.files);
            files.forEach(file => {
                const reader = new FileReader();
                reader.onload = (event) => {
                    const ext = file.name.split('.').pop()?.toLowerCase();
                    const langMap = { py: 'python', js: 'javascript', jsx: 'javascript', ts: 'typescript', tsx: 'typescript', json: 'json', md: 'markdown', css: 'css', html: 'html' };
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

    return (
        <div>
            <div className="empty-state">
                <FolderOpen className="empty-state-icon" />
                <div className="empty-state-title">No folder open</div>
                <div className="empty-state-description">Open files to start editing</div>
            </div>
            <div style={{ padding: '0 12px' }}>
                <button className="btn btn-primary" onClick={handleOpenFile} style={{ width: '100%', marginTop: 16 }}>
                    <Upload size={16} /> Open Files
                </button>
            </div>
        </div>
    );
}

export default FileExplorer;
