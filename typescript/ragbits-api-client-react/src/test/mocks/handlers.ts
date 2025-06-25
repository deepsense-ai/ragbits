import { http, HttpResponse } from 'msw'
import type { FeedbackResponse, TypedChatResponse } from '@ragbits/api-client'
import { ChatResponseType } from '@ragbits/api-client'
import { defaultConfigResponse } from '../utils'

export const handlers = [
    // Mock /api/config endpoint (GET)
    http.get('http://127.0.0.1:8000/api/config', () => {
        return HttpResponse.json(defaultConfigResponse)
    }),

    // Mock /api/feedback endpoint (POST)
    http.post('http://127.0.0.1:8000/api/feedback', async ({ request }) => {
        const _body = await request.json()
        const response: FeedbackResponse = {
            status: 'success',
        }
        return HttpResponse.json(response)
    }),

    // Mock /api/chat endpoint for streaming
    http.post('http://127.0.0.1:8000/api/chat', () => {
        const encoder = new TextEncoder()

        const stream = new ReadableStream({
            start(controller) {
                // Send multiple chunks to simulate streaming with proper TypedChatResponse format
                const chunks: string[] = [
                    `data: ${JSON.stringify({ type: ChatResponseType.TEXT, content: 'Hello' } as TypedChatResponse)}\n\n`,
                    `data: ${JSON.stringify({ type: ChatResponseType.TEXT, content: ' there!' } as TypedChatResponse)}\n\n`,
                    `data: ${JSON.stringify({ type: ChatResponseType.MESSAGE_ID, content: 'msg-123' } as TypedChatResponse)}\n\n`,
                    `data: ${JSON.stringify({ type: ChatResponseType.CONVERSATION_ID, content: 'conv-456' } as TypedChatResponse)}\n\n`,
                ]

                let index = 0
                const sendChunk = () => {
                    if (index < chunks.length) {
                        controller.enqueue(encoder.encode(chunks[index]))
                        index++
                        setTimeout(sendChunk, 10)
                    } else {
                        controller.close()
                    }
                }

                sendChunk()
            },
        })

        return new HttpResponse(stream, {
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                Connection: 'keep-alive',
            },
        })
    }),
]
