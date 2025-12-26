// Piston API - Free code execution service
// Supports 50+ languages with standard libraries
//
// Available Libraries:
// - Python: math, random, json, datetime, collections, re, os, sys, urllib, etc.
// - JavaScript/Node: All built-in modules (fs, path, http, crypto, etc.)
// - Java: All standard library classes
// - C/C++: Standard library (stdio, stdlib, string, math, vector, etc.)
// - Go, Rust, Ruby, PHP: Full standard libraries

const PISTON_URL = 'https://emkc.org/api/v2/piston';

export interface ExecuteResult {
    success: boolean;
    output: string;
    error?: string;
    runtime: string;
    language: string;
}

interface PistonResponse {
    run: {
        stdout: string;
        stderr: string;
        code: number;
        signal: string | null;
        output: string;
    };
    compile?: {
        stdout: string;
        stderr: string;
        code: number;
    };
    language: string;
    version: string;
}

// Language version mappings for Piston API
const LANGUAGE_VERSIONS: Record<string, { language: string; version: string }> = {
    python: { language: 'python', version: '3.10.0' },
    javascript: { language: 'javascript', version: '18.15.0' },
    typescript: { language: 'typescript', version: '5.0.3' },
    java: { language: 'java', version: '15.0.2' },
    c: { language: 'c', version: '10.2.0' },
    cpp: { language: 'c++', version: '10.2.0' },
    csharp: { language: 'csharp', version: '6.12.0' },
    go: { language: 'go', version: '1.16.2' },
    rust: { language: 'rust', version: '1.68.2' },
    ruby: { language: 'ruby', version: '3.0.1' },
    php: { language: 'php', version: '8.2.3' },
    swift: { language: 'swift', version: '5.3.3' },
    kotlin: { language: 'kotlin', version: '1.8.20' },
    r: { language: 'r', version: '4.1.1' },
    bash: { language: 'bash', version: '5.2.0' },
};

// Map file extensions to language
export function getLanguageFromFile(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    const extMap: Record<string, string> = {
        py: 'python',
        js: 'javascript',
        ts: 'typescript',
        jsx: 'javascript',
        tsx: 'typescript',
        java: 'java',
        c: 'c',
        cpp: 'cpp',
        cc: 'cpp',
        cs: 'csharp',
        go: 'go',
        rs: 'rust',
        rb: 'ruby',
        php: 'php',
        swift: 'swift',
        kt: 'kotlin',
        r: 'r',
        sh: 'bash',
    };
    return extMap[ext] || 'javascript';
}

export async function executeCode(
    code: string,
    language: string
): Promise<ExecuteResult> {
    const langConfig = LANGUAGE_VERSIONS[language];

    if (!langConfig) {
        return {
            success: false,
            output: '',
            error: `Language "${language}" is not supported. Supported: ${Object.keys(LANGUAGE_VERSIONS).join(', ')}`,
            runtime: '0ms',
            language,
        };
    }

    const startTime = Date.now();

    try {
        const response = await fetch(`${PISTON_URL}/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                language: langConfig.language,
                version: langConfig.version,
                files: [
                    {
                        name: `main.${getExtension(language)}`,
                        content: code,
                    },
                ],
                stdin: '',
                args: [],
                compile_timeout: 10000,
                run_timeout: 5000,
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: PistonResponse = await response.json();
        const runtime = `${Date.now() - startTime}ms`;

        // Check for compilation errors
        if (data.compile && data.compile.code !== 0) {
            return {
                success: false,
                output: data.compile.stdout,
                error: data.compile.stderr || 'Compilation failed',
                runtime,
                language: data.language,
            };
        }

        // Check for runtime errors  
        if (data.run.code !== 0 || data.run.stderr) {
            return {
                success: false,
                output: data.run.stdout,
                error: data.run.stderr || `Exit code: ${data.run.code}`,
                runtime,
                language: data.language,
            };
        }

        return {
            success: true,
            output: data.run.stdout || data.run.output || '(No output)',
            runtime,
            language: data.language,
        };
    } catch (error) {
        return {
            success: false,
            output: '',
            error: error instanceof Error ? error.message : 'Unknown error occurred',
            runtime: `${Date.now() - startTime}ms`,
            language,
        };
    }
}

function getExtension(language: string): string {
    const extMap: Record<string, string> = {
        python: 'py',
        javascript: 'js',
        typescript: 'ts',
        java: 'java',
        c: 'c',
        cpp: 'cpp',
        csharp: 'cs',
        go: 'go',
        rust: 'rs',
        ruby: 'rb',
        php: 'php',
        swift: 'swift',
        kotlin: 'kt',
        r: 'r',
        bash: 'sh',
    };
    return extMap[language] || 'txt';
}

// Get list of supported languages
export function getSupportedLanguages(): string[] {
    return Object.keys(LANGUAGE_VERSIONS);
}
