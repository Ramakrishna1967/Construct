import { useState, useRef } from 'react';
import {
    Upload,
    Github,
    FileCode2,
    FolderOpen,
    X,
    CheckCircle2,
    Loader2,
    Link,
    FileText
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../../store/useStore';
import './CodeUpload.css';

interface UploadedFile {
    name: string;
    content: string;
    language: string;
}

export function CodeUpload() {
    const [isOpen, setIsOpen] = useState(false);
    const [activeTab, setActiveTab] = useState<'paste' | 'upload' | 'github'>('paste');
    const [pasteContent, setPasteContent] = useState('');
    const [fileName, setFileName] = useState('code.py');
    const [githubUrl, setGithubUrl] = useState('');
    const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const { addFile, setActiveTab: setActiveFileTab } = useStore();

    const getLanguageFromExtension = (filename: string): string => {
        const ext = filename.split('.').pop()?.toLowerCase() || '';
        const langMap: Record<string, string> = {
            py: 'python', js: 'javascript', ts: 'typescript',
            jsx: 'javascript', tsx: 'typescript', java: 'java',
            cpp: 'cpp', c: 'c', cs: 'csharp', go: 'go',
            rs: 'rust', rb: 'ruby', php: 'php', swift: 'swift',
            kt: 'kotlin', md: 'markdown', json: 'json',
            html: 'html', css: 'css', sql: 'sql',
        };
        return langMap[ext] || 'plaintext';
    };

    const handlePasteSubmit = () => {
        if (!pasteContent.trim()) return;

        const id = `file-${Date.now()}`;
        addFile({
            id,
            name: fileName,
            path: `/${fileName}`,
            content: pasteContent,
            language: getLanguageFromExtension(fileName),
            isModified: false,
        });

        setActiveFileTab(id);
        setPasteContent('');
        setFileName('code.py');
        setIsOpen(false);
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files) return;

        const uploaded: UploadedFile[] = [];

        for (const file of Array.from(files)) {
            const content = await file.text();
            uploaded.push({
                name: file.name,
                content,
                language: getLanguageFromExtension(file.name),
            });
        }

        setUploadedFiles([...uploadedFiles, ...uploaded]);
    };

    const handleUploadSubmit = () => {
        uploadedFiles.forEach((file, index) => {
            const id = `file-${Date.now()}-${index}`;
            addFile({
                id,
                name: file.name,
                path: `/${file.name}`,
                content: file.content,
                language: file.language,
                isModified: false,
            });

            if (index === 0) {
                setActiveFileTab(id);
            }
        });

        setUploadedFiles([]);
        setIsOpen(false);
    };

    const handleGithubFetch = async () => {
        if (!githubUrl.trim()) return;

        setIsLoading(true);

        try {
            // Parse GitHub URL to get raw content
            // Example: https://github.com/user/repo/blob/main/file.py
            const match = githubUrl.match(/github\.com\/([^/]+)\/([^/]+)\/blob\/([^/]+)\/(.+)/);

            if (match) {
                const [, owner, repo, branch, path] = match;
                const rawUrl = `https://raw.githubusercontent.com/${owner}/${repo}/${branch}/${path}`;

                const response = await fetch(rawUrl);
                if (!response.ok) throw new Error('Failed to fetch file');

                const content = await response.text();
                const fileName = path.split('/').pop() || 'file.txt';

                const id = `file-${Date.now()}`;
                addFile({
                    id,
                    name: fileName,
                    path: `/${fileName}`,
                    content,
                    language: getLanguageFromExtension(fileName),
                    isModified: false,
                });

                setActiveFileTab(id);
                setGithubUrl('');
                setIsOpen(false);
            } else {
                alert('Please enter a valid GitHub file URL (e.g., https://github.com/user/repo/blob/main/file.py)');
            }
        } catch (error) {
            console.error('Failed to fetch from GitHub:', error);
            alert('Failed to fetch file from GitHub. Check the URL and try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const removeUploadedFile = (index: number) => {
        setUploadedFiles(uploadedFiles.filter((_, i) => i !== index));
    };

    return (
        <>
            {/* Trigger Button */}
            <button
                className="upload-trigger"
                onClick={() => setIsOpen(true)}
                title="Upload Code for Review"
            >
                <Upload size={16} />
                <span>Upload Code</span>
            </button>

            {/* Modal */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        className="upload-overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setIsOpen(false)}
                    >
                        <motion.div
                            className="upload-modal"
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="modal-header">
                                <h2>Upload Code for Review</h2>
                                <button className="close-btn" onClick={() => setIsOpen(false)}>
                                    <X size={20} />
                                </button>
                            </div>

                            {/* Tabs */}
                            <div className="upload-tabs">
                                <button
                                    className={activeTab === 'paste' ? 'active' : ''}
                                    onClick={() => setActiveTab('paste')}
                                >
                                    <FileCode2 size={16} />
                                    Paste Code
                                </button>
                                <button
                                    className={activeTab === 'upload' ? 'active' : ''}
                                    onClick={() => setActiveTab('upload')}
                                >
                                    <FolderOpen size={16} />
                                    Upload Files
                                </button>
                                <button
                                    className={activeTab === 'github' ? 'active' : ''}
                                    onClick={() => setActiveTab('github')}
                                >
                                    <Github size={16} />
                                    From GitHub
                                </button>
                            </div>

                            {/* Tab Content */}
                            <div className="upload-content">
                                {activeTab === 'paste' && (
                                    <div className="paste-tab">
                                        <div className="input-group">
                                            <label>File Name</label>
                                            <input
                                                type="text"
                                                value={fileName}
                                                onChange={(e) => setFileName(e.target.value)}
                                                placeholder="e.g., main.py, app.js"
                                            />
                                        </div>
                                        <div className="input-group">
                                            <label>Paste Your Code</label>
                                            <textarea
                                                value={pasteContent}
                                                onChange={(e) => setPasteContent(e.target.value)}
                                                placeholder="Paste your code here for AI review..."
                                                rows={15}
                                            />
                                        </div>
                                        <button
                                            className="submit-btn"
                                            onClick={handlePasteSubmit}
                                            disabled={!pasteContent.trim()}
                                        >
                                            <CheckCircle2 size={16} />
                                            Add for Review
                                        </button>
                                    </div>
                                )}

                                {activeTab === 'upload' && (
                                    <div className="upload-tab">
                                        <div
                                            className="drop-zone"
                                            onClick={() => fileInputRef.current?.click()}
                                        >
                                            <Upload size={32} />
                                            <p>Click to upload or drag & drop</p>
                                            <span>Supports all code files</span>
                                            <input
                                                ref={fileInputRef}
                                                type="file"
                                                multiple
                                                accept=".py,.js,.ts,.jsx,.tsx,.java,.cpp,.c,.go,.rs,.rb,.php,.swift,.kt,.md,.json,.html,.css,.sql,.txt"
                                                onChange={handleFileUpload}
                                                hidden
                                            />
                                        </div>

                                        {uploadedFiles.length > 0 && (
                                            <div className="uploaded-files">
                                                <h4>Files to Review ({uploadedFiles.length})</h4>
                                                {uploadedFiles.map((file, i) => (
                                                    <div key={i} className="uploaded-file">
                                                        <FileText size={14} />
                                                        <span>{file.name}</span>
                                                        <button onClick={() => removeUploadedFile(i)}>
                                                            <X size={14} />
                                                        </button>
                                                    </div>
                                                ))}
                                                <button
                                                    className="submit-btn"
                                                    onClick={handleUploadSubmit}
                                                >
                                                    <CheckCircle2 size={16} />
                                                    Add {uploadedFiles.length} Files for Review
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {activeTab === 'github' && (
                                    <div className="github-tab">
                                        <div className="input-group">
                                            <label>GitHub File URL</label>
                                            <div className="github-input">
                                                <Link size={16} />
                                                <input
                                                    type="text"
                                                    value={githubUrl}
                                                    onChange={(e) => setGithubUrl(e.target.value)}
                                                    placeholder="https://github.com/user/repo/blob/main/file.py"
                                                />
                                            </div>
                                            <span className="hint">
                                                Paste a direct link to any file on GitHub
                                            </span>
                                        </div>
                                        <button
                                            className="submit-btn"
                                            onClick={handleGithubFetch}
                                            disabled={!githubUrl.trim() || isLoading}
                                        >
                                            {isLoading ? (
                                                <>
                                                    <Loader2 size={16} className="spin" />
                                                    Fetching...
                                                </>
                                            ) : (
                                                <>
                                                    <Github size={16} />
                                                    Fetch & Review
                                                </>
                                            )}
                                        </button>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
