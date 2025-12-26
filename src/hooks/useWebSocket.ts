import { useCallback, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { API_CONFIG } from '../config/api';

interface WebSocketMessage {
    type: string;
    content?: string;
    agent?: string;
    session_id?: string;
    error?: string;
    [key: string]: unknown;
}

export function useWebSocket() {
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<number | null>(null);

    const {
        setConnected,
        setConnecting,
        setSessionId,
        addMessage,
        updateLastMessage,
        setProcessing,
        addSuggestion,
    } = useStore();

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        setConnecting(true);

        try {
            const ws = new WebSocket(API_CONFIG.WS_URL);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('✅ WebSocket connected');
                setConnected(true);
                setConnecting(false);
            };

            ws.onmessage = (event) => {
                try {
                    const data: WebSocketMessage = JSON.parse(event.data);
                    handleMessage(data);
                } catch (e) {
                    console.error('Failed to parse message:', e);
                }
            };

            ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                setConnecting(false);
            };

            ws.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                setConnected(false);
                setConnecting(false);

                // Attempt reconnection after 3 seconds
                reconnectTimeoutRef.current = window.setTimeout(() => {
                    console.log('🔄 Attempting to reconnect...');
                    connect();
                }, 3000);
            };
        } catch (error) {
            console.error('Failed to connect:', error);
            setConnecting(false);
        }
    }, [setConnected, setConnecting]);

    const handleMessage = useCallback((data: WebSocketMessage) => {
        switch (data.type) {
            case 'connected':
                if (data.session_id) {
                    setSessionId(data.session_id);
                }
                break;

            case 'stream_start':
                setProcessing(true);
                addMessage({
                    role: 'assistant',
                    content: '',
                    agent: data.agent,
                    isStreaming: true,
                });
                break;

            case 'stream_token':
                if (data.content) {
                    updateLastMessage(data.content);
                }
                break;

            case 'stream_end':
                setProcessing(false);
                break;

            case 'agent_response':
                addMessage({
                    role: 'assistant',
                    content: data.content || '',
                    agent: data.agent,
                });
                break;

            case 'suggestion':
                addSuggestion({
                    type: (data.severity as 'error' | 'warning' | 'info' | 'improvement') || 'info',
                    line: (data.line as number) || 1,
                    endLine: data.end_line as number | undefined,
                    message: data.message as string || '',
                    suggestion: data.suggestion as string | undefined,
                    agent: data.agent || 'reviewer',
                });
                break;

            case 'error':
                setProcessing(false);
                addMessage({
                    role: 'system',
                    content: `⚠️ Error: ${data.error || 'Unknown error'}`,
                });
                break;

            default:
                console.log('Unknown message type:', data.type);
        }
    }, [setSessionId, setProcessing, addMessage, updateLastMessage, addSuggestion]);

    const sendMessage = useCallback((message: string, code?: string) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return false;
        }

        const payload = {
            type: 'review',
            message,
            code,
        };

        wsRef.current.send(JSON.stringify(payload));

        // Add user message to store
        addMessage({
            role: 'user',
            content: message + (code ? `\n\n\`\`\`\n${code}\n\`\`\`` : ''),
        });

        setProcessing(true);
        return true;
    }, [addMessage, setProcessing]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        setConnected(false);
    }, [setConnected]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            disconnect();
        };
    }, [disconnect]);

    return {
        connect,
        disconnect,
        sendMessage,
        isConnected: useStore((s) => s.isConnected),
        isConnecting: useStore((s) => s.isConnecting),
    };
}
