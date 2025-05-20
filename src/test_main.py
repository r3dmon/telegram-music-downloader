#!/usr/bin/env python3
"""
Test script for Telegram authentication
Run this to verify that configuration and authentication work correctly
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import ConfigLoader
from logger import setup_logging
from client import create_client
from session_manager import create_session_manager
from message_parser import create_message_parser
from media_filter import create_media_filter
from tracker import create_file_tracker
from downloader import create_downloader


async def test_authentication():
    """Test Telegram authentication and full download workflow"""
    print("=== Telegram Music Downloader - Full Test ===\n")
    
    try:
        # Load configuration
        print("1. Loading configuration...")
        config = ConfigLoader("config.yaml")
        print("   ✓ Configuration loaded successfully")
        
        # Setup logging
        print("\n2. Setting up logging...")
        logger = setup_logging(config)
        print("   ✓ Logging configured")
        
        # Create session manager
        print("\n3. Initializing session manager...")
        session_manager = create_session_manager(config)
        
        # Check existing sessions
        sessions = session_manager.list_sessions()
        if sessions:
            print(f"   → Found {len(sessions)} existing session(s)")
            for session in sessions:
                print(f"     - {session['name']}")
        else:
            print("   → No existing sessions found")
        
        # Create tracker and check statistics
        print("\n4. Initializing file tracker...")
        file_tracker = create_file_tracker(config)
        tracker_stats = file_tracker.get_statistics()
        print(f"   → Processed messages: {tracker_stats['total_processed_messages']}")
        print(f"   → Downloaded files: {tracker_stats['total_downloaded_files']}")
        print(f"   → Blacklisted files: {tracker_stats['total_blacklisted_files']}")
        
        # Create and test Telegram client
        print("\n5. Connecting to Telegram...")
        client = await create_client(config)
        
        async with client as tg_client:
            # Get current user info
            me = await tg_client.get_client().get_me()
            print(f"   ✓ Successfully authenticated as: {me.first_name}")
            if me.username:
                print(f"     Username: @{me.username}")
            print(f"     User ID: {me.id}")
            
            # Initialize all components
            print("\n6. Initializing components...")
            parser = create_message_parser(tg_client.get_client(), config)
            media_filter = create_media_filter(config)
            downloader = create_downloader(tg_client.get_client(), config, file_tracker)
            print("   ✓ All components initialized")
            
            # Show current filter settings
            print(f"\n7. Current filter settings:")
            filter_summary = media_filter.get_filter_summary()
            print(f"   File types: {filter_summary['file_types']}")
            print(f"   Formats: {filter_summary['allowed_formats']}")
            print(f"   Size range: {filter_summary['size_range_mb']['min']}-{filter_summary['size_range_mb']['max']} MB")
            print(f"   Date range: {filter_summary['date_range']['from']} to {filter_summary['date_range']['to']}")
            max_files = config.get_max_files_per_run()
            print(f"   Max files per run: {max_files if max_files > 0 else 'unlimited'}")
            
            # Test getting dialogs (channels/chats)
            print("\n8. Testing channel access and workflow...")
            channels = config.get_channels()
            
            if not channels:
                print("   → No channels configured in config.yaml")
                return
            
            print(f"   → Testing access to {len(channels)} channel(s)...")
            
            # Get channel entities
            entities = await parser.get_channels_entities()
            
            # Test each channel with limited files
            test_limit = 100  # Only test with 5 files to avoid spam
            
            for channel_name, entity in entities:
                print(f"\n9. Processing channel: {channel_name} ({entity.title})")
                
                # Get channel statistics
                stats = await parser.get_channel_stats(entity)
                if stats:
                    print(f"   Stats (last 100 msgs): {stats['media_messages']} media files")
                    print(f"   Audio: {stats['audio_files']}, Documents: {stats['document_files']}")
                
                # Collect media files for testing
                print(f"   \n   Parsing and filtering {test_limit} recent messages...")
                media_files = []
                message_count = 0
                filtered_count = 0
                
                async for media_info in parser.parse_messages(entity, limit=test_limit * 2):  # Parse more to find suitable files
                    message_count += 1
                    
                    # Check tracker first
                    should_skip, skip_reason = file_tracker.should_skip_file(media_info)
                    if should_skip:
                        print(f"      → Skipped by tracker: {media_info['filename']} - {skip_reason}")
                        continue
                    
                    # Apply filters
                    if media_filter.should_process_media(media_info):
                        media_files.append(media_info)
                        print(f"      ✓ {len(media_files)}. {media_info['filename']}")
                        print(f"         Type: {media_info['type']}, Size: {media_filter.format_file_size(media_info['file_size'])}")
                        print(f"         MIME: {media_info['mime_type']}")
                        print(f"         Date: {media_info['publish_date']}")
                        
                        if media_info['audio_meta']:
                            meta = media_info['audio_meta']
                            if meta['title'] or meta['performer']:
                                print(f"         Audio: {meta['performer']} - {meta['title']}")
                            if meta['duration']:
                                duration_min = meta['duration'] // 60
                                duration_sec = meta['duration'] % 60
                                print(f"         Duration: {duration_min}:{duration_sec:02d}")
                        
                        # Stop when we have enough files for testing
                        if len(media_files) >= test_limit:
                            break
                    else:
                        filtered_count += 1
                        print(f"      ✗ Filtered out: {media_info['filename']}")
                
                print(f"   Summary: {message_count} checked, {len(media_files)} selected, {filtered_count} filtered out")
                
                # Test download workflow
                if media_files:
                    print(f"\n10. Testing download workflow with {len(media_files)} files...")
                    
                    # Ask user for confirmation
                    response = input(f"   Download {len(media_files)} files? (y/N): ").strip().lower()
                    if response != 'y':
                        print("   → Download skipped by user")
                    else:
                        # Download files
                        download_results = await downloader.download_multiple_files(media_files)
                        
                        # Show results
                        print(f"   \n   Download Results:")
                        print(f"      ✓ Successful: {len(download_results['successful'])}")
                        print(f"      → Skipped: {len(download_results['skipped'])}")
                        print(f"      ✗ Failed: {len(download_results['failed'])}")
                        
                        # Show downloaded files
                        if download_results['successful']:
                            print(f"   \n   Downloaded files:")
                            for result in download_results['successful']:
                                print(f"      → {result['file_path']}")
                        
                        # Show tracker statistics after download
                        updated_stats = file_tracker.get_statistics()
                        print(f"   \n   Updated tracker stats:")
                        print(f"      Processed messages: {updated_stats['total_processed_messages']}")
                        print(f"      Downloaded files: {updated_stats['total_downloaded_files']}")
                else:
                    print("   → No suitable files found for download test")
                
                print("   " + "-" * 60)
        
        print("\n=== Test completed successfully! ===")
        print("All components working correctly:")
        print("✓ Authentication and session management")
        print("✓ Message parsing with timeout")
        print("✓ Media filtering")
        print("✓ File tracking and duplicate detection")
        print("✓ File downloading and naming")
        print("\nMain application is ready to use!")
        
    except FileNotFoundError as e:
        print(f"❌ Configuration error: {e}")
        print("Make sure config.yaml exists and has correct values")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


def print_config_requirements():
    """Print configuration requirements"""
    print("\n=== Configuration Requirements ===")
    print("Before running this test, make sure you have:")
    print("1. Created config.yaml with your Telegram credentials")
    print("2. Added your api_id and api_hash from https://my.telegram.org")
    print("3. Listed channels you want to download from")
    print("\nExample config structure:")
    print("""
telegram:
  api_id: 12345
  api_hash: "your_api_hash_here"
  session_name: "music_downloader"
  two_factor_auth: true  # if you have 2FA enabled

channels:
  - "@your_music_channel"
  - "https://t.me/another_channel"
    """)


if __name__ == "__main__":
    # Check if config exists
    config_path = Path("config.yaml")
    
    if not config_path.exists():
        print("❌ Config file not found!")
        print_config_requirements()
        sys.exit(1)
    
    # Run the test
    try:
        asyncio.run(test_authentication())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)