import React from 'react'
import {
    render,
    renderHook,
    RenderOptions,
    RenderHookOptions,
} from '@testing-library/react'
import { RagbitsProvider } from '../RagbitsProvider'

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
) {
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
