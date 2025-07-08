import React from 'react'
import {
    render,
    renderHook,
    RenderOptions,
    RenderHookOptions,
    RenderResult,
} from '@testing-library/react'
import { RagbitsProvider } from '../src'
import type { ConfigResponse } from '@ragbits/api-client'

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
    baseUrl?: string
}

interface CustomRenderHookOptions<TProps>
    extends Omit<RenderHookOptions<TProps>, 'wrapper'> {
    baseUrl?: string
}

function createWrapper(baseUrl?: string) {
    return function Wrapper({ children }: { children: React.ReactNode }) {
        return <RagbitsProvider baseUrl={baseUrl}>{children}</RagbitsProvider>
    }
}

export function renderWithProvider(
    ui: React.ReactElement,
    options: CustomRenderOptions = {}
): RenderResult {
    const { baseUrl, ...renderOptions } = options

    return render(ui, {
        wrapper: createWrapper(baseUrl),
        ...renderOptions,
    })
}

export function renderHookWithProvider<TResult, TProps>(
    hook: (props: TProps) => TResult,
    options: CustomRenderHookOptions<TProps> = {}
) {
    const { baseUrl, ...renderOptions } = options

    return renderHook(hook, {
        wrapper: createWrapper(baseUrl),
        ...renderOptions,
    })
}

// Default config response used in most tests - matches Python classes
export const defaultConfigResponse: ConfigResponse = {
    feedback: {
        like: {
            enabled: true,
            form: {
                title: 'Like Form',
                type: 'object',
                required: ['like_reason'],
                properties: {
                    like_reason: {
                        title: 'Like Reason',
                        description: 'Why do you like this?',
                        type: 'string',
                        minLength: 1,
                    },
                },
            },
        },
        dislike: {
            enabled: true,
            form: {
                title: 'Dislike Form',
                type: 'object',
                required: ['issue_type', 'feedback'],
                properties: {
                    issue_type: {
                        title: 'Issue Type',
                        description: 'What was the issue?',
                        type: 'string',
                        enum: [
                            'Incorrect information',
                            'Not helpful',
                            'Unclear',
                            'Other',
                        ],
                    },
                    feedback: {
                        title: 'Feedback',
                        description: 'Please provide more details',
                        type: 'string',
                        minLength: 1,
                    },
                },
            },
        },
    },
    customization: null,
    user_settings: {
        form: {
            title: 'Chat Form',
            type: 'object',
            required: ['language'],
            properties: {
                language: {
                    title: 'Language',
                    description: 'Please select the language',
                    type: 'string',
                    enum: ['English', 'Polish'],
                },
            },
        },
    },
    debug_mode: true,
}
