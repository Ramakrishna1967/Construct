import { useApp } from '../../context/AppContext';
import { Wifi, WifiOff, GitBranch, Bell } from 'lucide-react';

function StatusBar() {
    const { connectionStatus, activeFile, isStreaming, currentAgent } = useApp();

    return (
        <div className="status-bar">
            <div className="status-bar-left">
                <div className="status-item">
                    <div className={`status-dot ${connectionStatus}`} />
                    <span>{connectionStatus === 'connected' ? 'AI Ready' : connectionStatus}</span>
                </div>
                {isStreaming && currentAgent && (
                    <div className="status-item">
                        <div className="loading-spinner" style={{ width: 12, height: 12 }} />
                        <span>{currentAgent}</span>
                    </div>
                )}
                <div className="status-item">
                    <GitBranch size={14} />
                    <span>main</span>
                </div>
            </div>
            <div className="status-bar-right">
                {activeFile && (
                    <div className="status-item">
                        <span>{activeFile.language || 'Plain Text'}</span>
                    </div>
                )}
                <div className="status-item"><span>UTF-8</span></div>
                <div className="status-item"><Bell size={14} /></div>
            </div>
        </div>
    );
}

export default StatusBar;
