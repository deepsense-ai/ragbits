import React from 'react'
import { describe, it, expect } from 'vitest'
import { act } from 'react'
import { waitFor } from '@testing-library/react'
import { renderHook } from '@testing-library/react'
import {
    RagbitsClient,
    FeedbackType,
    type TypedChatResponse,
} from 'ragbits-api-client'
import { useRagbitsCall, useRagbitsStream } from '../hooks'
import { RagbitsProvider } from '../RagbitsProvider'

function createWrapperWithClient(_client: RagbitsClient) {
    return function Wrapper({ children }: { children: React.ReactNode }) {
        return (
            <RagbitsProvider baseUrl="http://127.0.0.1:8000">
                {children}
            </RagbitsProvider>
        )
    }
}

describe('Integration Tests', () => {
    describe('API Client and React Hooks Integration', () => {
        it('should work with direct client instance and React hooks', async () => {
            // Test that both packages work together
            const client = new RagbitsClient({
                baseUrl: 'http://127.0.0.1:8000',
            })

            // Direct API call to real endpoint
            const directResponse = await client.makeRequest('/api/config')

            // React hook call to real endpoint
            const { result } = renderHook(() => useRagbitsCall('/api/config'), {
                wrapper: createWrapperWithClient(client),
            })

            await act(async () => {
                await result.current.call()
            })

            // Both should return the same data
            expect(directResponse).toEqual(result.current.data)
            expect(directResponse).toEqual({
                feedback: {
                    like: {
                        enabled: true,
                        form: {
                            title: 'Like Feedback',
                            fields: [
                                {
                                    name: 'comment',
                                    label: 'Comment',
                                    type: 'text',
                                    required: false,
                                },
                            ],
                        },
                    },
                    dislike: {
                        enabled: true,
                        form: {
                            title: 'Dislike Feedback',
                            fields: [
                                {
                                    name: 'reason',
                                    label: 'Reason',
                                    type: 'select',
                                    required: true,
                                    options: ['Incorrect', 'Unclear', 'Other'],
                                },
                            ],
                        },
                    },
                },
            })
        })

        it('should handle streaming in both packages consistently', async () => {
            const client = new RagbitsClient({
                baseUrl: 'http://127.0.0.1:8000',
            })

            // Direct streaming to real endpoint
            const directMessages: TypedChatResponse[] = []
            const directErrors: Error[] = []
            let directClosed = false

            const cancelDirectStream = client.makeStreamRequest(
                '/api/chat',
                { message: 'Direct stream', history: [] },
                {
                    onMessage: (data) => {
                        directMessages.push(data)
                        return Promise.resolve()
                    },
                    onError: (error) => {
                        directErrors.push(error)
                        return Promise.resolve()
                    },
                    onClose: () => {
                        directClosed = true
                    },
                }
            )

            // React hook streaming to real endpoint
            const { result } = renderHook(() => useRagbitsStream('/api/chat'), {
                wrapper: createWrapperWithClient(client),
            })

            const hookMessages: TypedChatResponse[] = []
            const hookErrors: string[] = []
            let hookClosed = false

            act(() => {
                result.current.stream(
                    { message: 'Hook stream', history: [] },
                    {
                        onMessage: (data) => {
                            hookMessages.push(data)
                        },
                        onError: (error) => {
                            hookErrors.push(error)
                        },
                        onClose: () => {
                            hookClosed = true
                        },
                    }
                )
            })

            // Wait for both streams to complete
            await waitFor(
                () => {
                    expect(directClosed).toBe(true)
                    expect(hookClosed).toBe(true)
                },
                { timeout: 3000 }
            )

            // Both should receive the same messages
            expect(directMessages).toHaveLength(4)
            expect(hookMessages).toHaveLength(4)
            expect(directMessages).toEqual(hookMessages)
            expect(directErrors).toHaveLength(0)
            expect(hookErrors).toHaveLength(0)

            // Cleanup
            cancelDirectStream()
        })

        it('should handle URL configuration consistently', async () => {
            const customBaseUrl = 'https://custom-api.example.com'

            // Direct client with custom URL
            const client = new RagbitsClient({ baseUrl: customBaseUrl })
            const directResponse = await client.makeRequest('/api/config')

            // React provider with custom URL
            function CustomWrapper({
                children,
            }: {
                children: React.ReactNode
            }) {
                return (
                    <RagbitsProvider baseUrl={customBaseUrl}>
                        {children}
                    </RagbitsProvider>
                )
            }

            const { result } = renderHook(() => useRagbitsCall('/api/config'), {
                wrapper: CustomWrapper,
            })

            await act(async () => {
                await result.current.call()
            })

            // Both should use the custom URL and return proper ConfigResponse
            expect(directResponse).toEqual(result.current.data)
            expect(directResponse).toEqual({
                feedback: {
                    like: { enabled: false, form: null },
                    dislike: { enabled: false, form: null },
                },
            })
        })

        it('should handle POST requests correctly', async () => {
            const client = new RagbitsClient({
                baseUrl: 'http://127.0.0.1:8000',
            })

            // Direct POST call to real endpoint
            const directResponse = await client.makeRequest('/api/feedback', {
                method: 'POST',
                body: {
                    message_id: 'msg-123',
                    feedback: FeedbackType.LIKE,
                    payload: { comment: 'Great response!' },
                },
            })

            // React hook POST call to real endpoint
            const { result } = renderHook(
                () => useRagbitsCall('/api/feedback'),
                { wrapper: createWrapperWithClient(client) }
            )

            await act(async () => {
                await result.current.call({
                    method: 'POST',
                    body: {
                        message_id: 'msg-123',
                        feedback: FeedbackType.LIKE,
                        payload: { comment: 'Great response!' },
                    },
                })
            })

            // Both should return the same FeedbackResponse
            expect(directResponse).toEqual(result.current.data)
            expect(directResponse).toEqual({
                status: 'success',
            })
        })
    })

    describe('Type Safety Integration', () => {
        it('should maintain type safety across both packages', async () => {
            // This test ensures that TypeScript types work correctly across both packages
            const client = new RagbitsClient({
                baseUrl: 'http://127.0.0.1:8000',
            })

            // Direct typed call to real endpoint
            const directResponse = await client.makeRequest('/api/config')

            // Hook typed call to real endpoint
            const { result } = renderHook(() => useRagbitsCall('/api/config'), {
                wrapper: createWrapperWithClient(client),
            })

            await act(async () => {
                await result.current.call()
            })

            // Types should be maintained and responses should match ConfigResponse structure
            expect(typeof directResponse).toBe('object')
            expect(typeof result.current.data).toBe('object')
            expect(directResponse).toEqual(result.current.data)
            expect(directResponse).toHaveProperty('feedback')
            expect(directResponse.feedback).toHaveProperty('like')
            expect(directResponse.feedback).toHaveProperty('dislike')
        })
    })

    describe('Performance and Memory Integration', () => {
        it('should not cause memory leaks when using both packages', async () => {
            // Test multiple rapid calls to ensure no memory leaks
            const client = new RagbitsClient({
                baseUrl: 'http://127.0.0.1:8000',
            })

            const { result } = renderHook(() => useRagbitsCall('/api/config'), {
                wrapper: createWrapperWithClient(client),
            })

            // Make multiple rapid calls
            for (let i = 0; i < 10; i++) {
                await act(async () => {
                    await result.current.call()
                })
            }

            expect(result.current.data).toHaveProperty('feedback')
            expect(result.current.error).toBeNull()
        })

        it('should handle multiple concurrent operations efficiently', async () => {
            const client = new RagbitsClient({
                baseUrl: 'http://127.0.0.1:8000',
            })

            const { result: callResult } = renderHook(
                () => useRagbitsCall('/api/config'),
                { wrapper: createWrapperWithClient(client) }
            )

            const { result: streamResult } = renderHook(
                () => useRagbitsStream('/api/chat'),
                { wrapper: createWrapperWithClient(client) }
            )

            // Start both operations concurrently
            const callPromise = act(async () => {
                await callResult.current.call()
            })

            const streamMessages: TypedChatResponse[] = []
            let streamClosed = false

            act(() => {
                streamResult.current.stream(
                    { message: 'Concurrent stream', history: [] },
                    {
                        onMessage: (data) => {
                            streamMessages.push(data)
                        },
                        onError: () => {},
                        onClose: () => {
                            streamClosed = true
                        },
                    }
                )
            })

            // Wait for both to complete
            await callPromise
            await waitFor(
                () => {
                    expect(streamClosed).toBe(true)
                },
                { timeout: 3000 }
            )

            // Both should complete successfully
            expect(callResult.current.data).toHaveProperty('feedback')
            expect(streamMessages).toHaveLength(4)
        })
    })
})
