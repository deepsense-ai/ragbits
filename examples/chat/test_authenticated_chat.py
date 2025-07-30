#!/usr/bin/env python3
"""
Test script for the Authenticated Chat Example

This script demonstrates how to interact with the authenticated chat API programmatically.
It shows the complete authentication workflow and chat interaction.

Usage:
    python examples/chat/test_authenticated_chat.py [--interactive]
"""

import asyncio
import json
import sys
from typing import Any

import httpx


class AuthenticatedChatTester:
    """Test client for the authenticated chat API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session_id: str | None = None
        self.current_user: dict[str, Any] | None = None

    async def test_config(self) -> None:
        """Test the configuration endpoint."""
        print("🔍 Testing API configuration...")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/api/config")
                if response.status_code == 200:
                    config = response.json()
                    auth_config = config.get("authentication", {})
                    print(f"✅ Authentication enabled: {auth_config.get('enabled', False)}")
                    print(f"🔧 Backend type: {auth_config.get('type', 'None')}")
                    print(f"💬 Conversation history: {config.get('conversation_history', False)}")
                else:
                    print(f"❌ Config request failed: {response.status_code}")
            except Exception as e:
                print(f"❌ Config request error: {e}")

    async def login(self, username: str, password: str) -> bool:
        """Login with username and password."""
        print(f"🔐 Attempting login for user: {username}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/auth/login", json={"username": username, "password": password}
                )

                result = response.json()
                if result.get("success") and result.get("session_id"):
                    self.session_id = result["session_id"]
                    self.current_user = result["user"]

                    print(f"✅ Login successful!")
                    print(f"👤 User: {self.current_user['full_name']} ({self.current_user['email']})")
                    print(f"🏷️  Roles: {', '.join(self.current_user['roles'])}")
                    print(f"🔑 Session: {self.session_id[:20]}...")
                    return True
                else:
                    print(f"❌ Login failed: {result.get('error_message', 'Unknown error')}")
                    return False
            except Exception as e:
                print(f"❌ Login error: {e}")
                return False

    async def chat(self, message: str, show_streaming: bool = True) -> None:
        """Send a chat message."""
        if not self.session_id:
            print("❌ Not logged in. Please login first.")
            return

        print(f"💬 You: {message}")
        print("🤖 Bot:", end=" " if show_streaming else "\n")

        headers = {"Authorization": f"Bearer {self.session_id}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response_text = ""
                references = []
                images = []

                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={"message": message, "history": [], "context": {}},
                    headers=headers,
                ) as response:
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])
                                    content_type = data.get("type")
                                    content = data.get("content")

                                    if content_type == "text":
                                        if show_streaming:
                                            print(content, end="", flush=True)
                                        response_text += content
                                    elif content_type == "reference":
                                        references.append(content)
                                    elif content_type == "image":
                                        images.append(content)
                                    elif content_type == "live_update":
                                        update_type = content.get("type", "")
                                        label = content.get("content", {}).get("label", "")
                                        if update_type == "START":
                                            print(f"\n🔄 {label}", flush=True)
                                        elif update_type == "FINISH":
                                            print(f"✅ {label}", flush=True)
                                        if show_streaming:
                                            print("🤖 Bot:", end=" ", flush=True)
                                    elif content_type == "followup_messages":
                                        print(f"\n\n💡 Suggested follow-ups:")
                                        for i, followup in enumerate(content, 1):
                                            print(f"   {i}. {followup}")
                                except json.JSONDecodeError:
                                    continue

                        if show_streaming:
                            print()  # New line after streaming response

                        # Show references and images
                        if references:
                            print("\n📚 References:")
                            for ref in references:
                                print(f"   📄 {ref['title']}: {ref['content'][:100]}...")

                        if images:
                            print("\n🖼️ Images:")
                            for img in images:
                                print(f"   🔗 {img['url']}")

                    else:
                        error_data = response.json()
                        print(f"\n❌ Chat failed: {error_data.get('detail', 'Unknown error')}")
            except Exception as e:
                print(f"\n❌ Chat error: {e}")

    async def logout(self) -> None:
        """Logout and clear session."""
        if not self.session_id:
            print("❌ Not logged in.")
            return

        print("🚪 Logging out...")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}/api/auth/logout", json={"session_id": self.session_id})

                result = response.json()
                if result.get("success"):
                    print("✅ Logout successful!")
                    self.session_id = None
                    self.current_user = None
                else:
                    print(f"❌ Logout failed: {result.get('error_message', 'Unknown error')}")
            except Exception as e:
                print(f"❌ Logout error: {e}")

    async def test_unauthenticated_request(self) -> None:
        """Test making a request without authentication."""
        print("🧪 Testing unauthenticated chat request...")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat", json={"message": "Hello without auth", "history": [], "context": {}}
                )

                if response.status_code == 401:
                    error_data = response.json()
                    print(f"✅ Correctly rejected: {error_data['detail']}")
                else:
                    print(f"❌ Unexpected response: {response.status_code}")
            except Exception as e:
                print(f"❌ Request error: {e}")


async def run_automated_test():
    """Run a comprehensive automated test."""
    tester = AuthenticatedChatTester()

    print("🧪 Automated Authentication Test")
    print("=" * 50)

    # Test configuration
    await tester.test_config()
    print()

    # Test unauthenticated request
    await tester.test_unauthenticated_request()
    print()

    # Test invalid login
    print("🧪 Testing invalid credentials...")
    await tester.login("invalid", "credentials")
    print()

    # Test valid login as regular user
    print("🧪 Testing login as regular user...")
    if await tester.login("alice", "alice123"):
        await tester.chat("Hello! Tell me about my profile.", show_streaming=False)
        print()
        await tester.chat("What can I do as a user?", show_streaming=False)
        print()
        await tester.logout()
    print()

    # Test login as admin
    print("🧪 Testing login as admin...")
    if await tester.login("admin", "admin123"):
        await tester.chat("Show me admin capabilities", show_streaming=False)
        print()
        await tester.chat("What admin features are available?", show_streaming=False)
        print()
        await tester.logout()
    print()

    # Test login as moderator
    print("🧪 Testing login as moderator...")
    if await tester.login("moderator", "mod123"):
        await tester.chat("What are my moderator responsibilities?", show_streaming=False)
        print()
        await tester.logout()

    print("\n✅ Automated test completed!")


async def run_interactive_test():
    """Run interactive test mode."""
    tester = AuthenticatedChatTester()

    print("🎮 Interactive Authenticated Chat Test")
    print("=" * 40)
    print("Available commands:")
    print("  login <username> <password> - Login")
    print("  chat <message>              - Send chat message")
    print("  logout                      - Logout")
    print("  test                        - Test unauthenticated request")
    print("  config                      - Show API configuration")
    print("  users                       - Show available test users")
    print("  quit                        - Exit")
    print()
    print("Available test users:")
    print("  admin / admin123       (admin, moderator, user)")
    print("  moderator / mod123     (moderator, user)")
    print("  alice / alice123       (user)")
    print("  bob / bob123           (user)")
    print()

    while True:
        try:
            if tester.current_user:
                prompt = f"[{tester.current_user['username']}] 🔤 "
            else:
                prompt = "[not logged in] 🔤 "

            command = input(prompt).strip().split(" ", 2)

            if not command or command[0] == "":
                continue
            elif command[0] == "quit":
                break
            elif command[0] == "login" and len(command) >= 3:
                await tester.login(command[1], command[2])
            elif command[0] == "chat" and len(command) >= 2:
                await tester.chat(" ".join(command[1:]))
            elif command[0] == "logout":
                await tester.logout()
            elif command[0] == "test":
                await tester.test_unauthenticated_request()
            elif command[0] == "config":
                await tester.test_config()
            elif command[0] == "users":
                print("Available test users:")
                print("  admin / admin123       (admin, moderator, user)")
                print("  moderator / mod123     (moderator, user)")
                print("  alice / alice123       (user)")
                print("  bob / bob123           (user)")
            else:
                print("Invalid command. Type 'quit' to exit.")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    if tester.session_id:
        await tester.logout()


async def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] in ["--interactive", "-i"]:
        await run_interactive_test()
    else:
        await run_automated_test()


if __name__ == "__main__":
    print("🚀 Authenticated Chat API Test")
    print("Make sure the API server is running first:")
    print("   python examples/chat/authenticated_chat.py")
    print()

    asyncio.run(main())
