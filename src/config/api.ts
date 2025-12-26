// API Configuration with Environment Variables
// These are automatically loaded from .env files by Vite

export const API_CONFIG = {
    // Backend URLs - Use environment variables for production
    BASE_URL: import.meta.env.VITE_API_URL || 'https://construct-eb7w.onrender.com',
    WS_URL: import.meta.env.VITE_WS_URL || 'wss://construct-eb7w.onrender.com/api/v1/ws',

    // Optional API Key for authenticated requests
    API_KEY: import.meta.env.VITE_API_KEY || '',

    // Endpoints
    ENDPOINTS: {
        HEALTH: '/health',
        REVIEW: '/api/v1/review',
        SESSIONS: '/api/v1/sessions',
        AUTH_GOOGLE: '/api/v1/auth/google',
        AUTH_ME: '/api/v1/auth/me',
        USAGE: '/api/v1/auth/usage',
        METRICS: '/api/v1/metrics/evaluations',
    },

    // AI Agents available in the backend
    AGENTS: ['supervisor', 'planner', 'researcher', 'coder', 'reviewer'] as const,
} as const;

export type AgentType = typeof API_CONFIG.AGENTS[number];

// Helper function to make authenticated API requests
export async function apiRequest<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const url = `${API_CONFIG.BASE_URL}${endpoint}`;

    const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    // Add API key if configured
    if (API_CONFIG.API_KEY) {
        (headers as Record<string, string>)['X-API-Key'] = API_CONFIG.API_KEY;
    }

    const response = await fetch(url, {
        ...options,
        headers,
    });

    if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
}

// Health check function
export async function checkBackendHealth(): Promise<{
    status: string;
    agents: boolean;
    redis: boolean;
    chromadb: boolean;
}> {
    try {
        const response = await fetch(`${API_CONFIG.BASE_URL}/health`);
        const data = await response.json();

        return {
            status: data.status || 'unknown',
            agents: true,
            redis: data.components?.redis?.status === 'healthy',
            chromadb: data.components?.chromadb?.status === 'healthy',
        };
    } catch {
        return {
            status: 'offline',
            agents: false,
            redis: false,
            chromadb: false,
        };
    }
}
