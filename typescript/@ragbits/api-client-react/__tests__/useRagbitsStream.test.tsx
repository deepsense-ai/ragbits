import React from 'react'
import { describe, it, expect } from 'vitest'
import { act } from 'react'
import { waitFor } from '@testing-library/react'
import { renderHook } from '@testing-library/react'
import { useRagbitsStream, RagbitsContextProvider } from '../src'
import { type ChatResponse } from '@ragbits/api-client'

function createWrapper() {
    return function Wrapper({ children }: { children: React.ReactNode }) {
        return (
            <RagbitsContextProvider baseUrl="http://127.0.0.1:8000">
                {children}
            </RagbitsContextProvider>
        )
    }
}

describe('useRagbitsStream', () => {
    it('should initialize with correct default state', () => {
        const { result } = renderHook(() => useRagbitsStream('/api/chat'), {
            wrapper: createWrapper(),
        })

        expect(result.current.error).toBeNull()
        expect(result.current.isStreaming).toBe(false)
        expect(typeof result.current.stream).toBe('function')
        expect(typeof result.current.cancel).toBe('function')
    })

    it('should handle streaming response', async () => {
        const { result } = renderHook(() => useRagbitsStream('/api/chat'), {
            wrapper: createWrapper(),
        })

        const messages: ChatResponse[] = []
        const errors: string[] = []
        let closed = false

        act(() => {
            result.current.stream(
                { message: 'Start streaming', history: [], context: {} },
                {
                    onMessage: (data) => {
                        messages.push(data)
                    },
                    onError: (error) => {
                        errors.push(error)
                    },
                    onClose: () => {
                        closed = true
                    },
                }
            )
        })

        expect(result.current.isStreaming).toBe(true)

        // Wait for stream to complete
        await waitFor(
            () => {
                expect(closed).toBe(true)
            },
            { timeout: 3000 }
        )

        expect(messages).toHaveLength(4)
        expect(messages[0]).toEqual({
            type: 'text',
            content: 'Hello',
        })
        expect(messages[1]).toEqual({
            type: 'text',
            content: ' there!',
        })
        expect(messages[2]).toEqual({
            type: 'message_id',
            content: 'msg-123',
        })
        expect(messages[3]).toEqual({
            type: 'conversation_id',
            content: 'conv-456',
        })
        expect(errors).toHaveLength(0)
        expect(result.current.isStreaming).toBe(false)
    })

    it('should handle stream cancellation', async () => {
        const { result } = renderHook(() => useRagbitsStream('/api/chat'), {
            wrapper: createWrapper(),
        })

        const messages: ChatResponse[] = []

        let cancelFn: (() => void) | undefined

        act(() => {
            cancelFn = result.current.stream(
                { message: 'Start streaming', history: [], context: {} },
                {
                    onMessage: (data) => {
                        messages.push(data)
                    },
                    onError: () => {},
                }
            )
        })

        expect(result.current.isStreaming).toBe(true)

        // Cancel the stream
        act(() => {
            if (cancelFn) {
                cancelFn()
            }
        })

        expect(result.current.isStreaming).toBe(false)

        // Wait a bit to ensure no more messages are received
        await new Promise((resolve) => setTimeout(resolve, 100))

        expect(messages.length).toBeLessThan(4) // Should not receive all messages
    })

    it('should handle multiple concurrent streams correctly', async () => {
        const { result } = renderHook(() => useRagbitsStream('/api/chat'), {
            wrapper: createWrapper(),
        })

        const messages1: ChatResponse[] = []
        const messages2: ChatResponse[] = []

        // Start first stream
        act(() => {
            result.current.stream(
                { message: 'Stream 1', history: [], context: {} },
                {
                    onMessage: (data) => {
                        messages1.push(data)
                    },
                    onError: () => {},
                }
            )
        })

        expect(result.current.isStreaming).toBe(true)

        // Start second stream while first is in progress (should cancel first)
        act(() => {
            result.current.stream(
                { message: 'Stream 2', history: [], context: {} },
                {
                    onMessage: (data) => {
                        messages2.push(data)
                    },
                    onError: () => {},
                }
            )
        })

        // Wait for second stream to complete
        await waitFor(
            () => {
                expect(result.current.isStreaming).toBe(false)
            },
            { timeout: 3000 }
        )

        // First stream should have been cancelled
        expect(messages1.length).toBeLessThan(4)
        // Second stream should complete
        expect(messages2).toHaveLength(4)
    })

    it('should use cancel method to stop streaming', async () => {
        const { result } = renderHook(() => useRagbitsStream('/api/chat'), {
            wrapper: createWrapper(),
        })

        const messages: ChatResponse[] = []

        act(() => {
            result.current.stream(
                { message: 'Start streaming', history: [], context: {} },
                {
                    onMessage: (data) => {
                        messages.push(data)
                    },
                    onError: () => {},
                }
            )
        })

        expect(result.current.isStreaming).toBe(true)

        // Use the cancel method
        act(() => {
            result.current.cancel()
        })

        expect(result.current.isStreaming).toBe(false)

        // Wait a bit to ensure no more messages are received
        await new Promise((resolve) => setTimeout(resolve, 100))

        expect(messages.length).toBeLessThan(4) // Should not receive all messages
    })
})
