import { useApp } from '../../context/AppContext';
import { Files, Search, GitBranch, MessageSquare, Settings, Sparkles, Terminal } from 'lucide-react';

function ActivityBar() {
    const { activePanel, setActivePanel } = useApp();

    const items = [
        { id: 'explorer', icon: Files, label: 'Explorer' },
        { id: 'search', icon: Search, label: 'Search' },
        { id: 'git', icon: GitBranch, label: 'Source Control' },
        { id: 'chat-history', icon: MessageSquare, label: 'Chat History' },
        { id: 'ai', icon: Sparkles, label: 'AI Features' },
    ];

    return (
        <div className="activity-bar">
            <div className="activity-bar-top">
                {items.map(item => (
                    <button
                        key={item.id}
                        className={`activity-bar-item ${activePanel === item.id ? 'active' : ''}`}
                        onClick={() => setActivePanel(item.id)}
                        title={item.label}
                    >
                        <item.icon size={24} />
                    </button>
                ))}
            </div>
            <div className="activity-bar-bottom">
                <button
                    className={`activity-bar-item ${activePanel === 'settings' ? 'active' : ''}`}
                    onClick={() => setActivePanel('settings')}
                    title="Settings"
                >
                    <Settings size={24} />
                </button>
            </div>
        </div>
    );
}

export default ActivityBar;
