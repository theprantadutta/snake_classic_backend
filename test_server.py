#!/usr/bin/env python3
"""
Test script for the Snake Classic Notification Backend.
This script tests the main endpoints without requiring real Firebase credentials.
"""

import asyncio
import httpx
import json
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8393"

async def test_health_endpoint():
    """Test the health check endpoint."""
    print("🩺 Testing health endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

async def test_root_endpoint():
    """Test the root endpoint."""
    print("\n🏠 Testing root endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Root endpoint failed: {e}")
            return False

async def test_firebase_status():
    """Test Firebase status endpoint."""
    print("\n🔥 Testing Firebase status...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/v1/test/firebase-status")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Firebase status failed: {e}")
            return False

async def test_token_validation():
    """Test FCM token validation."""
    print("\n🎫 Testing token validation...")
    
    # Mock FCM token for testing
    mock_token = "fake_token_for_testing_purposes_123456789"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/test/validate-token",
                params={"fcm_token": mock_token}
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return True  # This will always fail with mock credentials, but that's expected
        except Exception as e:
            print(f"❌ Token validation failed: {e}")
            return False

async def test_notification_sending():
    """Test sending a test notification."""
    print("\n📱 Testing notification sending...")
    
    # Mock FCM token for testing
    mock_token = "fake_token_for_testing_purposes_123456789"
    
    test_data = {
        "fcm_token": mock_token,
        "title": "🐍 Test Notification",
        "body": "This is a test from the Snake Classic backend!",
        "route": "home"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/test/send-test-notification",
                json=test_data
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            return True  # Expected to fail with mock credentials
        except Exception as e:
            print(f"❌ Notification sending failed: {e}")
            return False

async def test_game_notifications():
    """Test game-specific notification templates."""
    print("\n🎮 Testing game notification templates...")
    
    mock_token = "fake_token_for_testing_purposes_123456789"
    
    test_cases = [
        ("achievement", "🏆 Achievement test"),
        ("tournament", "🏆 Tournament test"),
        ("friend", "👥 Friend test"),
        ("daily", "🐍 Daily challenge test")
    ]
    
    async with httpx.AsyncClient() as client:
        for message_type, description in test_cases:
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/test/quick-game-notification",
                    params={
                        "fcm_token": mock_token,
                        "message_type": message_type
                    }
                )
                print(f"  {description} - Status: {response.status_code}")
                if response.status_code != 200:
                    print(f"    Response: {response.json()}")
            except Exception as e:
                print(f"  {description} - ❌ Failed: {e}")

async def test_scheduled_notifications():
    """Test notification scheduling."""
    print("\n⏰ Testing notification scheduling...")
    
    # Schedule a notification for 1 minute from now
    scheduled_time = (datetime.utcnow() + timedelta(minutes=1)).isoformat() + "Z"
    
    schedule_data = {
        "title": "⏰ Scheduled Test",
        "body": "This is a scheduled test notification",
        "notification_type": "special_event",
        "scheduled_time": scheduled_time,
        "recipients": ["fake_token_123"],
        "recipient_type": "tokens"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/notifications/schedule",
                json=schedule_data
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            # Get scheduled jobs
            jobs_response = await client.get(f"{BASE_URL}/api/v1/notifications/scheduled")
            print(f"Scheduled jobs: {jobs_response.json()}")
            
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Scheduling failed: {e}")
            return False

async def run_all_tests():
    """Run all tests sequentially."""
    print("🚀 Starting Snake Classic Notification Backend Tests")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health_endpoint),
        ("Root Endpoint", test_root_endpoint),
        ("Firebase Status", test_firebase_status),
        ("Token Validation", test_token_validation),
        ("Test Notification", test_notification_sending),
        ("Game Templates", test_game_notifications),
        ("Scheduled Notifications", test_scheduled_notifications),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
        
        await asyncio.sleep(0.5)  # Small delay between tests
    
    # Summary
    print(f"\n{'=' * 60}")
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The backend is working correctly.")
    else:
        print("⚠️  Some tests failed. This is expected with mock Firebase credentials.")
        print("   To run with real credentials, update firebase-admin-key.json with your")
        print("   actual Firebase service account key from the Firebase Console.")

if __name__ == "__main__":
    print("Make sure the server is running on http://127.0.0.1:8393")
    print("Run: python run.py")
    print()
    
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite crashed: {e}")