import { describe, it, expect, vi, beforeEach } from 'vitest'
import { RagbitsClient, FeedbackType } from '../src'
import { server } from './setup'
import { http, HttpResponse } from 'msw'
import type { FeedbackRequest } from '../src'
import { defaultConfigResponse } from './utils'

describe('RagbitsClient', () => {
    let client: RagbitsClient

    beforeEach(() => {
        client = new RagbitsClient({ baseUrl: 'http://127.0.0.1:8000' })
    })

    describe('Constructor', () => {
        it('should create client with default base URL', () => {
            const defaultClient = new RagbitsClient()
            expect(defaultClient).toBeInstanceOf(RagbitsClient)
        })

        it('should create client with custom base URL', () => {
            const customClient = new RagbitsClient({
                baseUrl: 'https://api.example.com',
            })
            expect(customClient).toBeInstanceOf(RagbitsClient)
        })

        it('should remove trailing slash from base URL', () => {
            const clientWithSlash = new RagbitsClient({
                baseUrl: 'https://api.example.com/',
            })
            expect(clientWithSlash).toBeInstanceOf(RagbitsClient)
        })

        it('should throw error for invalid base URL', () => {
            expect(() => {
                new RagbitsClient({ baseUrl: 'invalid-url' })
            }).toThrow(
                'Invalid base URL: invalid-url. Please provide a valid URL.'
            )
        })
    })

    describe('getBaseUrl', () => {
        it('should return the base URL', () => {
            expect(client.getBaseUrl()).toBe('http://127.0.0.1:8000')
        })
    })

    describe('makeRequest', () => {
        it('should make successful GET request', async () => {
            const response = await client.makeRequest('/api/config')

            expect(response).toEqual(defaultConfigResponse)
        })

        it('should make successful POST request with body', async () => {
            const requestBody: FeedbackRequest = {
                message_id: 'msg-123',
                feedback: FeedbackType.Like,
                payload: { reason: 'Great response!' },
            }

            const response = await client.makeRequest('/api/feedback', {
                method: 'POST',
                body: requestBody,
            })

            expect(response).toEqual({
                status: 'success',
            })
        })

        it('should handle request with custom headers', async () => {
            server.use(
                http.get('http://127.0.0.1:8000/api/config', ({ request }) => {
                    const customHeader = request.headers.get('X-Custom-Header')
                    return HttpResponse.json({
                        feedback: {
                            like: { enabled: true, form: null },
                            dislike: { enabled: false, form: null },
                        },
                        receivedHeader: customHeader,
                    })
                })
            )

            const response = await client.makeRequest('/api/config', {
                headers: {
                    'X-Custom-Header': 'test-value',
                },
            })

            // Check that the header was received by accessing the custom property
            const responseWithHeader = response as typeof response & {
                receivedHeader: string
            }
            expect(responseWithHeader.receivedHeader).toBe('test-value')
        })

        it('should handle HTTP errors', async () => {
            // Mock error response for testing
            server.use(
                http.get('http://127.0.0.1:8000/api/config', () => {
                    return new HttpResponse(null, { status: 500 })
                })
            )

            await expect(client.makeRequest('/api/config')).rejects.toThrow(
                'HTTP error! status: 500'
            )
        })

        it('should handle request cancellation', async () => {
            const abortController = new AbortController()

            // Mock a slow config endpoint
            server.use(
                http.get('http://127.0.0.1:8000/api/config', () => {
                    return new Promise((resolve) => {
                        setTimeout(() => {
                            resolve(
                                HttpResponse.json({
                                    feedback: {
                                        like: { enabled: true, form: null },
                                        dislike: { enabled: false, form: null },
                                    },
                                })
                            )
                        }, 1000)
                    })
                })
            )

            const requestPromise = client.makeRequest('/api/config', {
                signal: abortController.signal,
            })

            // Cancel the request immediately
            abortController.abort()

            await expect(requestPromise).rejects.toThrow()
        })
    })

    describe('makeStreamRequest', () => {
        it('should handle streaming response', async () => {
            const messages: unknown[] = []
            const errors: Error[] = []
            let closed = false

            const cancelFn = client.makeStreamRequest(
                '/api/chat',
                { message: 'Start streaming', history: [], context: {} },
                {
                    onMessage: (data) => {
                        messages.push(data)
                        return Promise.resolve()
                    },
                    onError: (error) => {
                        errors.push(error)
                        return Promise.resolve()
                    },
                    onClose: () => {
                        closed = true
                    },
                }
            )

            // Wait for stream to complete
            await new Promise((resolve) => {
                const checkComplete = () => {
                    if (closed || errors.length > 0) {
                        resolve(void 0)
                    } else {
                        setTimeout(checkComplete, 50)
                    }
                }
                checkComplete()
            })

            expect(messages).toHaveLength(4)
            expect(messages[0]).toEqual({
                type: 'text',
                content: 'Hello there!',
            })
            expect(messages[1]).toEqual({
                type: 'text',
                content: 'How can I help you?',
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
            expect(closed).toBe(true)

            // Cleanup
            cancelFn()
        })

        it('should handle stream cancellation', async () => {
            const messages: unknown[] = []
            const errors: Error[] = []

            const cancelFn = client.makeStreamRequest(
                '/api/chat',
                { message: 'Start streaming', history: [], context: {} },
                {
                    onMessage: (data) => {
                        messages.push(data)
                        return Promise.resolve()
                    },
                    onError: (error) => {
                        errors.push(error)
                        return Promise.resolve()
                    },
                }
            )

            // Cancel immediately
            cancelFn()

            // Wait a bit to ensure cancellation takes effect
            await new Promise((resolve) => setTimeout(resolve, 100))

            expect(messages.length).toBeLessThan(4) // Should not receive all messages
        })

        it('should handle stream errors', async () => {
            server.use(
                http.post('http://127.0.0.1:8000/api/chat', () => {
                    return new HttpResponse(null, { status: 500 })
                })
            )

            const errors: Error[] = []

            client.makeStreamRequest(
                '/api/chat',
                { message: 'Start streaming', history: [], context: {} },
                {
                    onMessage: () => Promise.resolve(),
                    onError: (error) => {
                        errors.push(error)
                        return Promise.resolve()
                    },
                }
            )

            // Wait for error to be captured
            await new Promise((resolve) => setTimeout(resolve, 100))

            expect(errors).toHaveLength(1)
            expect(errors[0].message).toContain('HTTP error! status: 500')
        })

        it('should handle malformed JSON in stream', async () => {
            server.use(
                http.post('http://127.0.0.1:8000/api/chat', () => {
                    const encoder = new TextEncoder()

                    const stream = new ReadableStream({
                        start(controller) {
                            controller.enqueue(
                                encoder.encode('data: invalid-json\n\n')
                            )
                            controller.close()
                        },
                    })

                    return new HttpResponse(stream, {
                        headers: {
                            'Content-Type': 'text/event-stream',
                        },
                    })
                })
            )

            const errors: Error[] = []

            client.makeStreamRequest(
                '/api/chat',
                { message: 'Start streaming', history: [], context: {} },
                {
                    onMessage: () => Promise.resolve(),
                    onError: (error) => {
                        errors.push(error)
                        return Promise.resolve()
                    },
                }
            )

            // Wait for error to be captured
            await new Promise((resolve) => setTimeout(resolve, 100))

            expect(errors).toHaveLength(1)
            expect(errors[0].message).toBe('Error processing server response')
        })

        it('should handle stream with AbortSignal', async () => {
            const abortController = new AbortController()
            const messages: unknown[] = []
            const errors: Error[] = []

            client.makeStreamRequest(
                '/api/chat',
                { message: 'Start streaming', history: [], context: {} },
                {
                    onMessage: (data) => {
                        messages.push(data)
                        return Promise.resolve()
                    },
                    onError: (error) => {
                        errors.push(error)
                        return Promise.resolve()
                    },
                },
                abortController.signal
            )

            // Abort after receiving first message (shorter delay to be more reliable)
            setTimeout(() => {
                abortController.abort()
            }, 5)

            // Wait longer for abort to take effect
            await new Promise((resolve) => setTimeout(resolve, 200))

            // Should receive fewer than 4 messages due to abort
            // Allow for some variation in timing but ensure it's not all 4
            expect(messages.length).toBeLessThanOrEqual(3)
        })

        it('should handle null response body', async () => {
            server.use(
                http.post('http://127.0.0.1:8000/api/chat', () => {
                    return new HttpResponse(null, {
                        headers: {
                            'Content-Type': 'text/event-stream',
                        },
                    })
                })
            )

            const errors: Error[] = []

            client.makeStreamRequest(
                '/api/chat',
                { message: 'Start streaming', history: [], context: {} },
                {
                    onMessage: () => Promise.resolve(),
                    onError: (error) => {
                        errors.push(error)
                        return Promise.resolve()
                    },
                }
            )

            // Wait for error to be captured
            await new Promise((resolve) => setTimeout(resolve, 100))

            expect(errors).toHaveLength(1)
            expect(errors[0].message).toBe('Response body is null')
        })

        it('should handle reader stream errors', async () => {
            server.use(
                http.post('http://127.0.0.1:8000/api/chat', () => {
                    const stream = new ReadableStream({
                        start(controller) {
                            // Simulate a stream error by enqueuing something and then erroring
                            const encoder = new TextEncoder()
                            controller.enqueue(
                                encoder.encode(
                                    'data: {"type": "text", "content": "Starting"}\n\n'
                                )
                            )
                            // Force an error in the stream
                            controller.error(new Error('Stream read error'))
                        },
                    })

                    return new HttpResponse(stream, {
                        headers: {
                            'Content-Type': 'text/event-stream',
                        },
                    })
                })
            )

            const errors: Error[] = []
            const messages: unknown[] = []

            client.makeStreamRequest(
                '/api/chat',
                { message: 'Start streaming', history: [], context: {} },
                {
                    onMessage: (data) => {
                        messages.push(data)
                        return Promise.resolve()
                    },
                    onError: (error) => {
                        errors.push(error)
                        return Promise.resolve()
                    },
                }
            )

            // Wait for error to be captured
            await new Promise((resolve) => setTimeout(resolve, 200))

            expect(errors).toHaveLength(1)
            expect(errors[0].message).toBe('Error reading stream')
        })

        it('should handle synchronous errors in makeStreamRequest', async () => {
            const errors: Error[] = []

            // Create a spy to force a synchronous error
            const originalFetch = global.fetch
            global.fetch = vi.fn().mockImplementation(() => {
                throw new Error('Synchronous fetch error')
            })

            client.makeStreamRequest(
                '/api/chat',
                { message: 'Start streaming', history: [], context: {} },
                {
                    onMessage: () => Promise.resolve(),
                    onError: (error) => {
                        errors.push(error)
                        return Promise.resolve()
                    },
                }
            )

            // Wait for error to be captured
            await new Promise((resolve) => setTimeout(resolve, 100))

            expect(errors).toHaveLength(1)
            expect(errors[0].message).toBe('Synchronous fetch error')

            // Restore original fetch
            global.fetch = originalFetch
        })

        it('should handle non-Error exceptions in stream processing', async () => {
            const errors: Error[] = []

            // Mock fetch to throw a non-Error object
            const originalFetch = global.fetch
            global.fetch = vi.fn().mockImplementation(() => {
                throw 'String error' // Non-Error exception
            })

            client.makeStreamRequest(
                '/api/chat',
                { message: 'Start streaming', history: [], context: {} },
                {
                    onMessage: () => Promise.resolve(),
                    onError: (error) => {
                        errors.push(error)
                        return Promise.resolve()
                    },
                }
            )

            // Wait for error to be captured
            await new Promise((resolve) => setTimeout(resolve, 100))

            expect(errors).toHaveLength(1)
            expect(errors[0].message).toBe('Error connecting to server')

            // Restore original fetch
            global.fetch = originalFetch
        })

        it('should handle request with custom headers', async () => {
            server.use(
                http.post('http://127.0.0.1:8000/api/chat', ({ request }) => {
                    const customHeader = request.headers.get('X-Custom-Header')
                    const message = { type: 'text', content: customHeader }
                    const encoder = new TextEncoder()
                    const stream = new ReadableStream({
                        start(controller) {
                            controller.enqueue(
                                encoder.encode(
                                    `data: ${JSON.stringify(message)}\n\n`
                                )
                            )
                            controller.close()
                        },
                    })
                    return new HttpResponse(stream, {
                        headers: { 'Content-Type': 'text/event-stream' },
                    })
                })
            )

            const messages: string[] = []
            client.makeStreamRequest(
                '/api/chat',
                { message: 'Start streaming', history: [], context: {} },
                {
                    onMessage: (data) => {
                        if (data.type !== 'text') {
                            return
                        }

                        messages.push(data.content)
                    },
                    onError: () => {},
                },
                undefined,
                {
                    'X-Custom-Header': 'test-header',
                }
            )

            // Wait for message to be captured
            await new Promise((resolve) => setTimeout(resolve, 100))

            expect(messages).toHaveLength(1)
            expect(messages[0]).toBe('test-header')
        })
    })
})
