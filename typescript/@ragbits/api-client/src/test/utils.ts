import type { ConfigResponse } from '../types'

// Shared config response for tests
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
            form: null,
        },
    },
    customization: null,
    debug_mode: false,
}
