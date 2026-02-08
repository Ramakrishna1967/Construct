import { useApp } from '../../context/AppContext';
import FileExplorer from './FileExplorer';
import ChatHistory from './ChatHistory';
import { Search, Settings, Sparkles } from 'lucide-react';

function Sidebar() {
    const { activePanel, sidebarCollapsed } = useApp();

    const getPanelTitle = () => {
        const titles = {
            explorer: 'Explorer',
            search: 'Search',
            'chat-history': 'Chat History',
            git: 'Source Control',
            ai: 'AI Features',
            settings: 'Settings',
        };
        return titles[activePanel] || 'Explorer';
    };

    const renderContent = () => {
        switch (activePanel) {
            case 'explorer': return <FileExplorer />;
            case 'chat-history': return <ChatHistory />;
            case 'search': return <SearchPanel />;
            case 'ai': return <AIPanel />;
            case 'settings': return <SettingsPanel />;
            default: return <FileExplorer />;
        }
    };

    return (
        <div className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
            <div className="sidebar-header"><span>{getPanelTitle()}</span></div>
            <div className="sidebar-content">{renderContent()}</div>
        </div>
    );
}

function SearchPanel() {
    return (
        <div className="empty-state">
            <Search className="empty-state-icon" />
            <div className="empty-state-title">Search Files</div>
            <div className="empty-state-description">Search across your workspace</div>
        </div>
    );
}

function AIPanel() {
    return (
        <div className="empty-state">
            <Sparkles className="empty-state-icon" />
            <div className="empty-state-title">AI Features</div>
            <div className="empty-state-description">Code review, refactoring, debugging</div>
        </div>
    );
}

function SettingsPanel() {
    return (
        <div className="empty-state">
            <Settings className="empty-state-icon" />
            <div className="empty-state-title">Settings</div>
            <div className="empty-state-description">Configure your IDE</div>
        </div>
    );
}

export default Sidebar;
