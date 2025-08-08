# Authenticated Chat Example

This example demonstrates how to create a chat interface with user authentication using Ragbits Chat.

## Features

- 🔐 **User Authentication**: Login/logout with username/password
- 👤 **Role-based Access**: Different user roles (admin, moderator, user) with specific capabilities
- 🛡️ **Secure Sessions**: Session-based authentication with Bearer tokens
- 📊 **Personalized Responses**: User-specific chat responses based on profile and roles
- 🔄 **Live Updates**: Role-specific live updates during processing
- 📚 **User Context**: Reference documents with user profile information
- 🎨 **UI Customization**: Custom welcome messages, headers, and branding
- 📝 **Feedback System**: Like/dislike forms with custom Pydantic models
- ⚙️ **User Settings**: Configurable user preferences (e.g., language selection)

## Files

- `authenticated_chat.py` - Main authenticated chat implementation
- `README_authenticated.md` - This documentation

## Quick Start

### 1. Start the Server

#### Full Authentication Support (Recommended)
```bash
# From the examples/chat directory - includes login/logout endpoints
uv run python authenticated_chat.py
```

#### Alternative Methods
```bash
# From project root
python examples/chat/authenticated_chat.py

# Via CLI with authentication support
uv run ragbits api run examples.chat.authenticated_chat:MyAuthenticatedChat --auth examples.chat.authenticated_chat:get_auth_backend
```

The server will start at `http://127.0.0.1:8000` with a web interface.

**Note**: When using the CLI, include the `--auth` flag with the authentication backend factory function to enable full authentication features including login/logout endpoints.

### 2. Test Users

The example includes these test users:

| Username  | Password  | Roles                    | Description         |
|-----------|-----------|--------------------------|---------------------|
| `admin`   | `admin123` | admin, moderator, user  | System administrator |
| `moderator` | `mod123` | moderator, user        | Community moderator |
| `alice`   | `alice123` | user                   | Regular user        |
| `bob`     | `bob123`   | user                   | Regular user        |

### 3. Authentication Workflow

#### Web Interface
1. Open `http://127.0.0.1:8000` in your browser
2. Use the login form with any test user credentials
3. Start chatting after successful authentication

#### API Endpoints
1. **Login**: `POST /api/auth/login`
   ```json
   {
     "username": "admin",
     "password": "admin123"
   }
   ```

2. **Chat**: `POST /api/chat` (with Bearer token)
   ```bash
   Authorization: Bearer <session_id>
   ```

3. **Logout**: `POST /api/auth/logout`
   ```json
   {
     "session_id": "<session_id>"
   }
   ```

## Testing

You can test the authentication functionality using:

### Web Interface Testing
1. Start the server: `python examples/chat/authenticated_chat.py`
2. Open `http://127.0.0.1:8000` in your browser
3. Use the login form with any of the test user credentials
4. Test different roles and their specific features

### API Testing with curl
```bash
# Login
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Chat (replace <session_id> with the session_id from login response)
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <session_id>" \
  -d '{"message": "Hello!"}'

# Logout
curl -X POST http://127.0.0.1:8000/api/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<session_id>"}'
```

## Example Chat Interactions

### As Admin User
```
💬 You: What admin features are available?
🤖 Bot: As an administrator, you have full system access including:
- User management and permissions
- System configuration and monitoring
- Content moderation capabilities
- Administrative dashboards and reports
```

### As Regular User
```
💬 You: Tell me about my profile
🤖 Bot: Hello Alice Johnson! You're logged in as 'alice' with user role.
Your profile shows you're part of the Marketing department.
```

## Architecture
### ListAuthBackend
- In-memory user storage with hashed passwords
- Session management with expiration
- User roles and metadata support
- Suitable for development and small deployments

### Role-based Features
- **Admin**: Full system access, admin-specific live updates, special admin profile images
- **Moderator**: Content moderation features with policy checks and content guidelines
- **User**: Standard chat features with personalized responses and user-specific context

## Customization

### Adding New Users
Edit the `get_auth_backend()` factory function in `authenticated_chat.py`:

```python
users = [
    {
        "username": "newuser",
        "password": "newpass123",
        "email": "newuser@example.com",
        "full_name": "New User",
        "roles": ["user"],
        "metadata": {"department": "Engineering"}
    }
]
```


### Role-specific Responses
Modify the `chat()` method to customize responses based on user roles:

```python
# Get user info from context
user_info = context.state.get("authenticated_user") if context else None
user_roles = user_info.roles if user_info else []

if "admin" in user_roles:
    yield self.create_text_response("🔧 Admin-specific content...")
elif "moderator" in user_roles:
    yield self.create_text_response("🛡️ Moderator-specific content...")
```

### UI Customization

The example demonstrates UI customization features:

```python
from ragbits.chat.interface.ui_customization import HeaderCustomization, UICustomization

ui_customization = UICustomization(
    header=HeaderCustomization(
        title="🔐 Authenticated Ragbits Chat",
        subtitle="by deepsense.ai - Secure Chat Experience",
        logo="🛡️"
    ),
    welcome_message="🔐 **Welcome to Authenticated Ragbits Chat!**\n\n..."
)
```

### Feedback Configuration

Custom feedback forms using Pydantic models:

```python
from ragbits.chat.interface.forms import FeedbackConfig

feedback_config = FeedbackConfig(
    like_enabled=True,
    like_form=LikeFormExample,  # Custom Pydantic model
    dislike_enabled=True,
    dislike_form=DislikeFormExample,  # Custom Pydantic model
)
```

## Security Notes

- Passwords are hashed using bcrypt in `ListAuthBackend`
- Sessions have configurable expiration times
- Bearer tokens are used for API authentication
- CORS is configured for web interface access
- State signatures prevent tampering with conversation state
