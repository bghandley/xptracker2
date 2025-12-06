#!/usr/bin/env python3
"""
Cleanup script to wipe all user data files (except xp_data.json which is the template).
Use this to reset the app to a clean state.
"""
import os
import glob

def cleanup_users():
    """Delete all user data files."""
    # Find all xp_data_*.json files (user files)
    user_files = glob.glob("xp_data_*.json")
    
    if not user_files:
        print("✅ No user files found. Database is clean.")
        return
    
    print(f"🗑️  Found {len(user_files)} user file(s):")
    for f in user_files:
        print(f"   - {f}")
    
    confirm = input("\n⚠️  Delete all these files? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Cancelled.")
        return
    
    for f in user_files:
        try:
            os.remove(f)
            print(f"✅ Deleted: {f}")
        except Exception as e:
            print(f"❌ Failed to delete {f}: {e}")
    
    print("\n✅ Cleanup complete!")

if __name__ == "__main__":
    cleanup_users()
