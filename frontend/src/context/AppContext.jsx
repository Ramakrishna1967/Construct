import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'https://construct-eb7w.onrender.com';
const WS_URL = BACKEND_URL.replace('https', 'wss').replace('http', 'ws') + '/ws';

const initialState = {
    activePanel: 'explorer',
    sidebarCollapsed: false,
    openFiles: [],
    activeFile: null,
    messages: [],
    isStreaming: false,
    currentAgent: null,
    connectionStatus: 'disconnected',
};

const AppContext = createContext(null);

export function AppProvider({ children }) {
    const [state, setState] = useState(initialState);
    const wsRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);

    const updateState = useCallback((updates) => {
        setState(prev => ({ ...prev, ...updates }));
    }, []);

    const connectWebSocket = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        updateState({ connectionStatus: 'connecting' });
        console.log('🔌 Connecting to:', WS_URL);

        try {
            wsRef.current = new WebSocket(WS_URL);

            wsRef.current.onopen = () => {
                console.log('✅ Connected!');
                updateState({ connectionStatus: 'connected' });
            };

            wsRef.current.onclose = (e) => {
                console.log('❌ Disconnected:', e.code);
                updateState({ connectionStatus: 'disconnected', isStreaming: false });
                reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
            };

            wsRef.current.onerror = () => {
                updateState({ connectionStatus: 'disconnected' });
            };

            wsRef.current.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                } catch (e) {
                    console.error('Parse error:', e);
                }
            };
        } catch (error) {
            console.error('WebSocket error:', error);
            updateState({ connectionStatus: 'disconnected' });
        }
    }, [updateState]);

    const handleMessage = useCallback((data) => {
        switch (data.type) {
            case 'token':
                setState(prev => {
                    const messages = [...prev.messages];
                    const lastMsg = messages[messages.length - 1];
                    if (lastMsg && lastMsg.role === 'assistant' && lastMsg.sender === data.sender) {
                        lastMsg.content += data.content;
                    } else {
                        messages.push({
                            id: Date.now(),
                            role: 'assistant',
                            content: data.content,
                            sender: data.sender,
                            timestamp: new Date(),
                        });
                    }
                    return { ...prev, messages, isStreaming: true, currentAgent: data.sender };
                });
                break;

            case 'complete':
                updateState({ isStreaming: false, currentAgent: null });
                break;

            case 'error':
                setState(prev => ({
                    ...prev,
                    messages: [...prev.messages, {
                        id: Date.now(),
                        role: 'error',
                        content: data.error || data.details,
                        timestamp: new Date(),
                    }],
                    isStreaming: false,
                }));
                break;
        }
    }, [updateState]);

    useEffect(() => {
        connectWebSocket();
        return () => {
            if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
            if (wsRef.current) wsRef.current.close();
        };
    }, [connectWebSocket]);

    const sendMessage = useCallback((content) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return;
        }

        setState(prev => ({
            ...prev,
            messages: [...prev.messages, {
                id: Date.now(),
                role: 'user',
                content,
                timestamp: new Date(),
            }],
            isStreaming: true,
        }));

        wsRef.current.send(content);
    }, []);

    const setActivePanel = useCallback((panel) => updateState({ activePanel: panel }), [updateState]);
    const toggleSidebar = useCallback(() => setState(prev => ({ ...prev, sidebarCollapsed: !prev.sidebarCollapsed })), []);

    const openFile = useCallback((file) => {
        setState(prev => {
            const exists = prev.openFiles.find(f => f.id === file.id);
            if (exists) {
                return { ...prev, activeFile: file };
            }
            return { ...prev, openFiles: [...prev.openFiles, file], activeFile: file };
        });
    }, []);

    const closeFile = useCallback((fileId) => {
        setState(prev => {
            const newOpenFiles = prev.openFiles.filter(f => f.id !== fileId);
            const newActiveFile = prev.activeFile?.id === fileId
                ? newOpenFiles[newOpenFiles.length - 1] || null
                : prev.activeFile;
            return { ...prev, openFiles: newOpenFiles, activeFile: newActiveFile };
        });
    }, []);

    const value = {
        ...state,
        sendMessage,
        setActivePanel,
        toggleSidebar,
        openFile,
        closeFile,
        connectionStatus: state.connectionStatus,
    };

    return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
    const context = useContext(AppContext);
    if (!context) throw new Error('useApp must be used within AppProvider');
    return context;
}
