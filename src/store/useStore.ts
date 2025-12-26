import { create } from 'zustand';

// Types
export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
    agent?: string;
    isStreaming?: boolean;
}

export interface FileTab {
    id: string;
    name: string;
    path: string;
    content: string;
    language: string;
    isModified: boolean;
}

export interface ReviewSuggestion {
    id: string;
    type: 'error' | 'warning' | 'info' | 'improvement';
    line: number;
    endLine?: number;
    message: string;
    suggestion?: string;
    agent: string;
}

export interface TerminalOutput {
    id: string;
    type: 'command' | 'output' | 'error' | 'info';
    content: string;
    timestamp: Date;
}

interface AppState {
    // Connection
    isConnected: boolean;
    isConnecting: boolean;
    sessionId: string | null;

    // UI State
    sidebarOpen: boolean;
    aiPanelOpen: boolean;
    terminalOpen: boolean;
    activeTab: string | null;

    // Files
    files: FileTab[];

    // AI Chat
    messages: Message[];
    isProcessing: boolean;

    // Review
    suggestions: ReviewSuggestion[];

    // Terminal / Code Execution
    terminalOutput: TerminalOutput[];
    isExecuting: boolean;

    // Actions
    setConnected: (connected: boolean) => void;
    setConnecting: (connecting: boolean) => void;
    setSessionId: (id: string | null) => void;
    toggleSidebar: () => void;
    toggleAIPanel: () => void;
    toggleTerminal: () => void;
    setActiveTab: (id: string | null) => void;
    addFile: (file: FileTab) => void;
    updateFile: (id: string, content: string) => void;
    closeFile: (id: string) => void;
    addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
    updateLastMessage: (content: string) => void;
    setProcessing: (processing: boolean) => void;
    addSuggestion: (suggestion: Omit<ReviewSuggestion, 'id'>) => void;
    clearSuggestions: () => void;
    addTerminalOutput: (output: Omit<TerminalOutput, 'id' | 'timestamp'>) => void;
    clearTerminal: () => void;
    setExecuting: (executing: boolean) => void;
    reset: () => void;
}

export const useStore = create<AppState>((set) => ({
    // Initial state
    isConnected: false,
    isConnecting: false,
    sessionId: null,
    sidebarOpen: true,
    aiPanelOpen: true,
    terminalOpen: true,
    activeTab: 'demo',
    files: [
        {
            id: 'demo',
            name: 'example_api.py',
            path: '/example_api.py',
            language: 'python',
            isModified: false,
            content: `# 🔍 Sample Code for AI Review
# Click "Review" in the AI Panel to analyze this code with 5 AI agents!

# ✅ Standard library imports work!
import math
import random
import json
from datetime import datetime
from collections import Counter

# Math operations
print("📐 Math Library:")
print(f"  π = {math.pi:.6f}")
print(f"  √2 = {math.sqrt(2):.6f}")
print(f"  sin(45°) = {math.sin(math.radians(45)):.6f}")

# Random number generation
print("\\n🎲 Random Numbers:")
numbers = [random.randint(1, 100) for _ in range(5)]
print(f"  Random list: {numbers}")
print(f"  Random choice: {random.choice(['Apple', 'Banana', 'Cherry'])}")

# Date and time
print("\\n📅 Date & Time:")
now = datetime.now()
print(f"  Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

# JSON processing
print("\\n📦 JSON Processing:")
data = {"name": "Construct IDE", "version": "2.0", "features": ["AI Review", "Compiler"]}
print(f"  {json.dumps(data, indent=2)}")

# Collections
print("\\n📊 Collections:")
words = ['apple', 'banana', 'apple', 'cherry', 'banana', 'apple']
word_count = Counter(words)
print(f"  Word counts: {dict(word_count)}")

print("\\n✅ All imports working! Try your own code.")
`,
        },
    ],
    messages: [
        {
            id: 'welcome',
            role: 'assistant',
            content: "👋 Welcome to **Construct IDE**! I'm your AI code review assistant powered by 5 specialized agents:\n\n• **Supervisor** - Orchestrates the review process\n• **Planner** - Designs the analysis strategy\n• **Researcher** - Searches for patterns and best practices\n• **Coder** - Suggests code improvements\n• **Reviewer** - Provides final assessment\n\nPaste your code and I'll help you improve it!",
            timestamp: new Date(),
            agent: 'supervisor',
        },
    ],
    isProcessing: false,
    suggestions: [],
    terminalOutput: [
        {
            id: 'init',
            type: 'info',
            content: '$ Construct IDE v2.0.0 - Code Compiler Ready',
            timestamp: new Date(),
        },
        {
            id: 'init2',
            type: 'info',
            content: '✓ Supported: Python, JavaScript, TypeScript, Java, C++, Go, Rust, and more',
            timestamp: new Date(),
        },
        {
            id: 'init3',
            type: 'info',
            content: '→ Click ▶ Run or press Ctrl+Enter to execute code\n',
            timestamp: new Date(),
        },
    ],
    isExecuting: false,

    // Actions
    setConnected: (connected) => set({ isConnected: connected }),
    setConnecting: (connecting) => set({ isConnecting: connecting }),
    setSessionId: (id) => set({ sessionId: id }),

    toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
    toggleAIPanel: () => set((s) => ({ aiPanelOpen: !s.aiPanelOpen })),
    toggleTerminal: () => set((s) => ({ terminalOpen: !s.terminalOpen })),

    setActiveTab: (id) => set({ activeTab: id }),

    addFile: (file) => set((s) => ({
        files: [...s.files, file],
        activeTab: file.id,
    })),

    updateFile: (id, content) => set((s) => ({
        files: s.files.map((f) =>
            f.id === id ? { ...f, content, isModified: true } : f
        ),
    })),

    closeFile: (id) => set((s) => {
        const newFiles = s.files.filter((f) => f.id !== id);
        const newActiveTab = s.activeTab === id
            ? newFiles[newFiles.length - 1]?.id ?? null
            : s.activeTab;
        return { files: newFiles, activeTab: newActiveTab };
    }),

    addMessage: (message) => set((s) => ({
        messages: [
            ...s.messages,
            {
                ...message,
                id: `msg-${Date.now()}`,
                timestamp: new Date(),
            },
        ],
    })),

    updateLastMessage: (content) => set((s) => ({
        messages: s.messages.map((m, i) =>
            i === s.messages.length - 1 ? { ...m, content, isStreaming: false } : m
        ),
    })),

    setProcessing: (processing) => set({ isProcessing: processing }),

    addSuggestion: (suggestion) => set((s) => ({
        suggestions: [
            ...s.suggestions,
            { ...suggestion, id: `sug-${Date.now()}-${Math.random()}` },
        ],
    })),

    clearSuggestions: () => set({ suggestions: [] }),

    addTerminalOutput: (output) => set((s) => ({
        terminalOutput: [
            ...s.terminalOutput,
            {
                ...output,
                id: `term-${Date.now()}-${Math.random()}`,
                timestamp: new Date(),
            },
        ],
    })),

    clearTerminal: () => set({ terminalOutput: [] }),

    setExecuting: (executing) => set({ isExecuting: executing }),

    reset: () => set({
        isConnected: false,
        sessionId: null,
        messages: [],
        suggestions: [],
        terminalOutput: [],
    }),
}));
