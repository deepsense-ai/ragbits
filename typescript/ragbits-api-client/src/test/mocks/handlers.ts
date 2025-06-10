import { http, HttpResponse } from 'msw'

export const handlers = [
    // Config endpoint with conditional error handling
    http.get('http://127.0.0.1:8000/api/config', ({ request }) => {
        const url = new URL(request.url)
        if (url.searchParams.get('error') === 'true') {
            return new HttpResponse(null, { status: 500 })
        }

        return HttpResponse.json({
            feedback: {
                like: {
                    enabled: true,
                    form: {
                        title: 'Like Feedback',
                        fields: [
                            {
                                name: 'reason',
                                label: 'What did you like?',
                                type: 'text',
                                required: false,
                            },
                        ],
                    },
                },
                dislike: {
                    enabled: true,
                    form: null,
                },
            },
        })
    }),

    // Feedback endpoint
    http.post('http://127.0.0.1:8000/api/feedback', async ({ request }) => {
        const _body = await request.json()
        return HttpResponse.json({
            status: 'success',
        })
    }),

    // Chat streaming endpoint
    http.post('http://127.0.0.1:8000/api/chat', ({ request }) => {
        const url = new URL(request.url)

        // Handle different test scenarios
        if (url.searchParams.get('error') === 'true') {
            return new HttpResponse(null, { status: 500 })
        }

        if (url.searchParams.get('malformed') === 'true') {
            const encoder = new TextEncoder()
            const stream = new ReadableStream({
                start(controller) {
                    controller.enqueue(encoder.encode('data: invalid-json\n\n'))
                    controller.close()
                },
            })
            return new HttpResponse(stream, {
                headers: { 'Content-Type': 'text/event-stream' },
            })
        }

        if (url.searchParams.get('empty') === 'true') {
            return new HttpResponse(null, {
                headers: { 'Content-Type': 'text/event-stream' },
            })
        }

        if (url.searchParams.get('slow') === 'true') {
            return new Promise((resolve) => {
                setTimeout(() => {
                    resolve(
                        HttpResponse.json({
                            type: 'text',
                            content: 'Slow response',
                        })
                    )
                }, 1000)
            })
        }

        const encoder = new TextEncoder()

        const stream = new ReadableStream({
            start(controller) {
                const messages = [
                    { type: 'text', content: 'Hello there!' },
                    { type: 'text', content: 'How can I help you?' },
                    { type: 'message_id', content: 'msg-123' },
                    { type: 'conversation_id', content: 'conv-456' },
                ]

                messages.forEach((message, index) => {
                    setTimeout(() => {
                        controller.enqueue(
                            encoder.encode(
                                `data: ${JSON.stringify(message)}\n\n`
                            )
                        )
                        if (index === messages.length - 1) {
                            controller.close()
                        }
                    }, index * 10)
                })
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
