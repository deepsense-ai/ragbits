import type { ConfigResponse } from '../src'

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
}
