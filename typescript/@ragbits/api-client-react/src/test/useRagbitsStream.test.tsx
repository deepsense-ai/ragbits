import React from 'react'
import { describe, it, expect } from 'vitest'
import { act } from 'react'
import { waitFor } from '@testing-library/react'
import { renderHook } from '@testing-library/react'
import { useRagbitsStream } from '../hooks'
import { RagbitsProvider } from '../RagbitsProvider'
import { ChatResponseType, type TypedChatResponse } from '@ragbits/api-client'

function createWrapper() {
    return function Wrapper({ children }: { children: React.ReactNode }) {
        return <RagbitsProvider>{children}</RagbitsProvider>
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

        const messages: TypedChatResponse[] = []
        const errors: string[] = []
        let closed = false

        act(() => {
            result.current.stream(
                { message: 'Start streaming', history: [] },
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
            type: ChatResponseType.TEXT,
            content: 'Hello',
        })
        expect(messages[1]).toEqual({
            type: ChatResponseType.TEXT,
            content: ' there!',
        })
        expect(messages[2]).toEqual({
            type: ChatResponseType.MESSAGE_ID,
            content: 'msg-123',
        })
        expect(messages[3]).toEqual({
            type: ChatResponseType.CONVERSATION_ID,
            content: 'conv-456',
        })
        expect(errors).toHaveLength(0)
        expect(result.current.isStreaming).toBe(false)
    })

    it('should handle stream cancellation', async () => {
        const { result } = renderHook(() => useRagbitsStream('/api/chat'), {
            wrapper: createWrapper(),
        })

        const messages: TypedChatResponse[] = []

        let cancelFn: (() => void) | undefined

        act(() => {
            cancelFn = result.current.stream(
                { message: 'Start streaming', history: [] },
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

        const messages1: TypedChatResponse[] = []
        const messages2: TypedChatResponse[] = []

        // Start first stream
        act(() => {
            result.current.stream(
                { message: 'Stream 1', history: [] },
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
                { message: 'Stream 2', history: [] },
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

        const messages: TypedChatResponse[] = []

        act(() => {
            result.current.stream(
                { message: 'Start streaming', history: [] },
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
