import { MessageSquare } from 'lucide-react';

function ChatHistory() {
    const sessions = [
        { id: 1, title: 'Code Review Session', time: '2 hours ago' },
        { id: 2, title: 'Debugging Help', time: 'Yesterday' },
        { id: 3, title: 'Refactoring Suggestions', time: '3 days ago' },
    ];

    return (
        <div>
            <div style={{ padding: '8px 12px' }}>
                {sessions.map(session => (
                    <div key={session.id} className="session-item">
                        <MessageSquare size={14} />
                        <div>
                            <div className="session-item-title">{session.title}</div>
                            <div className="session-item-meta">{session.time}</div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default ChatHistory;
