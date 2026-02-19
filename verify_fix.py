import asyncio
import time
import datetime
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.services import scheduler

async def test_drift_detection():
    print("Testing clock drift detection...")
    
    # Mock dependencies
    bot_mock = AsyncMock()
    
    # Simulate current state
    now_wall = datetime.datetime.now(scheduler.KYIV_TZ).timestamp()
    now_mono = time.monotonic()
    
    # Scenario 1: Normal operation (1 min passed for both)
    # ---------------------------------------------------
    print("\n[Test 1] Normal operation (60s wall, 60s mono)")
    scheduler._last_check_time = now_wall - 60
    scheduler._last_check_mono = now_mono - 60
    
    # We patch get_all_users to return empty list so logic proceeds past drift check 
    # but doesn't crash on DB
    with patch('bot.services.scheduler.get_all_users', new_callable=AsyncMock) as mock_users:
        mock_users.return_value = []
        await scheduler.notify_before_class(bot_mock)
        
        # Check if updated
        if scheduler._last_check_time > now_wall - 1:
            print("PASS: Timestamps updated normally.")
        else:
            print(f"FAIL: Timestamps not updated? {scheduler._last_check_time}")

    # Scenario 2: Sleep detected (5s wall, 3600s mono)
    # ------------------------------------------------
    print("\n[Test 2] Sleep simulation (5s wall, 3600s mono)")
    # Reset to "before sleep"
    now_wall = datetime.datetime.now(scheduler.KYIV_TZ).timestamp()
    now_mono = time.monotonic()
    
    # Set LAST check to be 5 seconds ago in wall time, but 1 hour ago in mono time
    # Tricky: logic is delta = current - last
    # We want delta_wall = 5, delta_mono = 3600
    scheduler._last_check_time = now_wall - 5
    scheduler._last_check_mono = now_mono - 3600
    
    # Capture print output? Or just check if get_all_users was called (it shouldn't be if it returns early)
    with patch('bot.services.scheduler.get_all_users', new_callable=AsyncMock) as mock_users:
        await scheduler.notify_before_class(bot_mock)
        
        if mock_users.called:
            print("FAIL: get_all_users WAS called! Drift detection failed.")
        else:
            print("PASS: get_all_users NOT called. Notification loop skipped.")
            
        # Verify timestamps updated to current to prevent loop
        if scheduler._last_check_time > now_wall - 1:
            print("PASS: Timestamps updated to reset drift.")
        else:
            print("FAIL: Timestamps not reset.")

if __name__ == "__main__":
    asyncio.run(test_drift_detection())
