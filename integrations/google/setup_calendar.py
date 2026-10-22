#!/usr/bin/env python3
"""
Google Calendar Integration Setup
Guides you through setting up Google Calendar API access
"""

import subprocess
import sys
from pathlib import Path

CREDENTIALS_DIR = Path.home() / ".config" / "solo-empire" / "integrations" / "google"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"
REQUIREMENTS_FILE = Path(__file__).parent / "requirements.txt"


def check_dependencies():
    """Check if required Python packages are installed"""
    print("🔍 Checking dependencies...")

    try:
        import google.oauth2.credentials  # noqa: F401 - import probes that the package is installed
        import google_auth_oauthlib  # noqa: F401 - import probes that the package is installed
        import googleapiclient  # noqa: F401 - import probes that the package is installed

        print("✅ All dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print(f"\n📦 Install with: pip install -r {REQUIREMENTS_FILE}")
        return False


def setup_credentials():
    """Guide user through Google Cloud Console setup"""
    print("\n" + "=" * 70)
    print("🔑 Google Calendar API Setup")
    print("=" * 70)

    print("\n📋 Follow these steps to create credentials:\n")

    print("1️⃣  Go to Google Cloud Console:")
    print("   🔗 https://console.cloud.google.com/\n")

    print("2️⃣  Create a new project (or select existing):")
    print("   - Click the project dropdown at the top")
    print("   - Click 'NEW PROJECT'")
    print("   - Name it 'Solo Empire Integrations' (or any name)")
    print("   - Click 'CREATE'\n")

    print("3️⃣  Enable Google Calendar API:")
    print("   - Go to 'APIs & Services' → 'Library'")
    print("   - Search for 'Google Calendar API'")
    print("   - Click on it and press 'ENABLE'\n")

    print("4️⃣  Configure OAuth consent screen:")
    print("   - Go to 'APIs & Services' → 'OAuth consent screen'")
    print("   - Choose 'External' and click 'CREATE'")
    print("   - Fill in:")
    print("     • App name: Solo Empire")
    print("     • User support email: your email")
    print("     • Developer contact: your email")
    print("   - Click 'SAVE AND CONTINUE' through all steps")
    print("   - On 'Test users' step, add your Google email\n")

    print("5️⃣  Create OAuth 2.0 credentials:")
    print("   - Go to 'APIs & Services' → 'Credentials'")
    print("   - Click '+ CREATE CREDENTIALS' → 'OAuth client ID'")
    print("   - Application type: 'Desktop app'")
    print("   - Name: 'Solo Empire Calendar'")
    print("   - Click 'CREATE'\n")

    print("6️⃣  Download credentials:")
    print("   - Click the download button (⬇️) on your new credentials")
    print("   - Save the file as: credentials.json")
    print(f"   - Move it to: {CREDENTIALS_FILE}\n")

    print("7️⃣  Verify setup:")
    if CREDENTIALS_FILE.exists():
        print(f"   ✅ Found: {CREDENTIALS_FILE}")
        return True
    print(f"   ⏳ Waiting for: {CREDENTIALS_FILE}")
    print("\n💡 Tip: You can manually copy the file to:")
    print(f"   {CREDENTIALS_FILE}")
    return False


def test_connection():
    """Test the Google Calendar connection"""
    print("\n🧪 Testing Google Calendar connection...")

    try:
        # Import here to avoid errors if not set up yet
        sys.path.insert(0, str(Path(__file__).parent))
        from calendar_sync import get_credentials, sync_calendar_events

        creds = get_credentials()
        if not creds:
            print("❌ Could not get credentials")
            return False

        print("✅ Authentication successful!")

        # Try to sync a small range
        print("\n📅 Syncing last 7 days of events...")
        count = sync_calendar_events(days_ahead=0, days_back=7)

        if count > 0:
            print(f"\n✅ Successfully synced {count} events!")
            return True
        print("\n⚠️  No events found (this is OK if your calendar is empty)")
        return True

    except Exception as e:  # noqa: BLE001 - interactive setup: report any failure and return False
        print(f"❌ Connection test failed: {e}")
        return False


def create_cron_job():
    """Create a cron job for automatic syncing"""
    print("\n⏰ Setting up automatic sync...")

    script_path = Path(__file__).parent / "calendar_sync.py"

    print("\n📋 To sync automatically, add this to your crontab:")
    print("\n   crontab -e\n")
    print("   # Add this line to sync every hour:")
    print(
        f"   0 * * * * /usr/bin/python3 {script_path} --sync >> /tmp/calendar_sync.log 2>&1\n"
    )

    print("💡 Or sync manually whenever you want:")
    print(f"   python3 {script_path} --sync\n")


def main():
    """Main setup flow"""
    print("\n🚀 Google Calendar Integration Setup\n")

    # Step 1: Check dependencies
    if not check_dependencies():
        install = input("\n📦 Install dependencies now? (y/n): ").lower()
        if install == "y":
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE],
                check=False,  # success is verified by re-running check_dependencies()
            )
            if not check_dependencies():
                print("\n❌ Failed to install dependencies. Please install manually.")
                sys.exit(1)
        else:
            sys.exit(1)

    # Step 2: Setup credentials
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

    if not CREDENTIALS_FILE.exists():
        if not setup_credentials():
            input("\n⏸️  Press Enter after you've downloaded credentials.json...")

            if not CREDENTIALS_FILE.exists():
                print(f"\n❌ Still can't find {CREDENTIALS_FILE}")
                print("   Please manually copy the file and run this script again.")
                sys.exit(1)
    else:
        print(f"\n✅ Found existing credentials: {CREDENTIALS_FILE}")

    # Step 3: Test connection
    if not test_connection():
        print("\n❌ Setup incomplete. Please check your credentials and try again.")
        sys.exit(1)

    # Step 4: Setup cron (optional)
    setup_cron = input("\n⏰ Setup automatic sync? (y/n): ").lower()
    if setup_cron == "y":
        create_cron_job()

    # Success!
    print("\n" + "=" * 70)
    print("✅ Google Calendar Integration Complete!")
    print("=" * 70)
    print("\n📚 Available commands:")
    print(f"   python3 {Path(__file__).parent / 'calendar_sync.py'} --sync")
    print(f"   python3 {Path(__file__).parent / 'calendar_sync.py'} --upcoming 7")
    print(f"   python3 {Path(__file__).parent / 'calendar_sync.py'} --stats")
    print("\n🎉 You can now query your calendar through Solo Empire!")
    print("   Example: 'Show me my upcoming events this week'\n")


if __name__ == "__main__":
    main()
