"""
Test script to demonstrate the authentication workflow with RagbitsAPI.
"""

import asyncio
import json
from typing import Any

import httpx


class AuthTestClient:
    """Test client for authentication workflow."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session_id: str | None = None

    async def login(self, username: str, password: str) -> dict[str, Any]:
        """Login and store session_id."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/auth/login", json={"username": username, "password": password}
            )

            result = response.json()
            if result.get("success") and result.get("session_id"):
                self.session_id = result["session_id"]
                print(f"✅ Login successful for {username}")
                print(f"👤 User: {result['user']['full_name']} ({result['user']['email']})")
                print(f"🔑 Session ID: {self.session_id[:20]}...")
                print(f"👥 Roles: {', '.join(result['user']['roles'])}")
            else:
                print(f"❌ Login failed: {result.get('error_message')}")

            return result

    async def chat(self, message: str) -> None:
        """Send a chat message with authentication."""
        if not self.session_id:
            print("❌ Not logged in")
            return

        headers = {"Authorization": f"Bearer {self.session_id}"}

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={"message": message, "history": [], "context": {}},
                    headers=headers,
                ) as response:
                    if response.status_code == 200:
                        print(f"💬 You: {message}")
                        print("🤖 Bot: ", end="", flush=True)

                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data = json.loads(line[6:])
                                if data["type"] == "text":
                                    print(data["content"], end="", flush=True)
                        print()  # New line after response
                    else:
                        error_data = response.json()
                        print(f"❌ Chat failed: {error_data.get('detail', 'Unknown error')}")
            except Exception as e:
                print(f"❌ Chat error: {e}")

    async def logout(self) -> None:
        """Logout and clear session."""
        if not self.session_id:
            print("❌ Not logged in")
            return

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/api/auth/logout", json={"session_id": self.session_id})

            result = response.json()
            if result.get("success"):
                print("✅ Logout successful")
                self.session_id = None
            else:
                print(f"❌ Logout failed: {result.get('error_message')}")

    async def test_unauthenticated_chat(self) -> None:
        """Test chat without authentication."""
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


async def test_authentication_workflow():
    """Test the complete authentication workflow."""
    client = AuthTestClient()

    print("🧪 Testing Complete Authentication Workflow")
    print("=" * 50)

    # Test 1: Unauthenticated request
    await client.test_unauthenticated_chat()
    print()

    # Test 2: Invalid login
    print("🧪 Testing invalid login...")
    await client.login("invalid", "credentials")
    print()

    # Test 3: Valid login
    print("🧪 Testing valid login...")
    await client.login("admin", "admin123")
    print()

    # Test 4: Authenticated chat
    print("🧪 Testing authenticated chat...")
    await client.chat("Hello, I am authenticated!")
    print()
    await client.chat("What are my user details?")
    print()

    # Test 5: Logout
    print("🧪 Testing logout...")
    await client.logout()
    print()

    # Test 6: Chat after logout
    print("🧪 Testing chat after logout...")
    await client.chat("This should fail")
    print()

    # Test 7: Login as different user
    print("🧪 Testing login as different user...")
    await client.login("jane", "secret456")
    print()
    await client.chat("Hello as Jane!")
    await client.logout()


async def interactive_test():
    """Interactive test mode."""
    client = AuthTestClient()

    print("🎮 Interactive Authentication Test")
    print("Commands: login <user> <pass>, chat <message>, logout, quit")
    print("Available users: admin/admin123, john/password123, jane/secret456")
    print()

    while True:
        try:
            command = input("🔤 Command: ").strip().split(" ", 2)

            if command[0] == "quit":
                break
            elif command[0] == "login" and len(command) >= 3:
                await client.login(command[1], command[2])
            elif command[0] == "chat" and len(command) >= 2:
                await client.chat(" ".join(command[1:]))
            elif command[0] == "logout":
                await client.logout()
            else:
                print("Invalid command. Use: login <user> <pass>, chat <message>, logout, quit")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    if client.session_id:
        await client.logout()


async def main():
    """Main test function."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        await interactive_test()
    else:
        await test_authentication_workflow()


if __name__ == "__main__":
    print("🚀 Make sure to run the API server first:")
    print("   python -m ragbits.chat.auth.api_example")
    print()
    asyncio.run(main())
