#!/usr/bin/env python3
"""
Telegram Music Downloader - Main Application
Downloads audio files from Telegram channels with filtering and tracking
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any

# Import all modules
from config_loader import ConfigLoader
from logger import setup_logging
from client import create_client
from session_manager import create_session_manager
from message_parser import create_message_parser
from media_filter import create_media_filter
from tracker import create_file_tracker
from downloader import create_downloader


class TelegramMusicDownloader:
    def __init__(self, config_path: str = "config.yaml"):
        # Load configuration
        self.config = ConfigLoader(config_path)
        
        # Setup logging
        self.logger = setup_logging(self.config)
        self.logger.info("=== Telegram Music Downloader Started ===")
        
        # Initialize components
        self.session_manager = create_session_manager(self.config)
        self.file_tracker = create_file_tracker(self.config)
        self.media_filter = create_media_filter(self.config)
        
        # Will be initialized after connection
        self.client = None
        self.parser = None
        self.downloader = None
    
    async def initialize_client(self):
        """Initialize Telegram client and related components"""
        self.logger.info("Initializing Telegram client...")
        self.client = await create_client(self.config)
        
        await self.client.connect()
        if not self.client.client.is_connected():
            raise RuntimeError("Failed to connect to Telegram")
        
        # Initialize parser and downloader
        self.parser = create_message_parser(self.client.get_client(), self.config)
        self.downloader = create_downloader(self.client.get_client(), self.config, self.file_tracker)
        
        self.logger.info("Client initialized successfully")

    async def run_download_session(self, max_files: int = 0) -> Dict[str, Any]:
        """Run complete download session for all configured channels"""
        session_results = {
            'channels_processed': 0,
            'total_files_found': 0,
            'total_files_downloaded': 0,
            'total_files_skipped': 0,
            'total_files_failed': 0,
            'channels_details': []
        }
        
        try:
            # Get all channels
            channels = self.config.get_channels()
            if not channels:
                self.logger.warning("No channels configured")
                return session_results
            
            # Get channel entities
            entities = await self.parser.get_channels_entities()
            if not entities:
                self.logger.error("No accessible channels found")
                return session_results
            
            # Get max files per run from config
            config_max_files = self.config.get_max_files_per_run()
            if config_max_files > 0:
                max_files = min(max_files, config_max_files) if max_files > 0 else config_max_files
            
            self.logger.info(f"Processing {len(entities)} channels, max files: {max_files if max_files > 0 else 'unlimited'}")
            
            # Process each channel
            files_downloaded_total = 0
            for channel_name, entity in entities:
                # Проверяем общий лимит скачиваний для всех каналов
                if max_files > 0 and files_downloaded_total >= max_files:
                    self.logger.info(f"Reached maximum files limit ({max_files}), stopping")
                    break
                
                # Вычисляем сколько файлов осталось скачать для данного канала
                remaining_files = max_files - files_downloaded_total if max_files > 0 else 0
                
                # Обрабатываем канал
                channel_result = await self._process_channel(
                    channel_name, 
                    entity, 
                    remaining_files
                )
                
                session_results['channels_details'].append(channel_result)
                session_results['channels_processed'] += 1
                session_results['total_files_found'] += channel_result['files_found']
                session_results['total_files_downloaded'] += channel_result['files_downloaded']
                session_results['total_files_skipped'] += channel_result['files_skipped']
                session_results['total_files_failed'] += channel_result['files_failed']
                
                files_downloaded_total += channel_result['files_downloaded']
            
            return session_results
            
        except Exception as e:
            self.logger.error(f"Error during download session: {e}")
            raise
    

    async def _process_channel(self, channel_name: str, entity, max_files: int = 0) -> Dict[str, Any]:
        """Process single channel - parse, filter, and download files"""
        self.logger.info(f"Processing channel: {channel_name} ({entity.title})")
        
        channel_result = {
            'channel_name': channel_name,
            'channel_title': entity.title,
            'files_found': 0,
            'files_downloaded': 0,
            'files_skipped': 0,
            'files_failed': 0,
            'downloaded_files': []
        }
        
        try:
            # Get channel statistics first
            stats = await self.parser.get_channel_stats(entity)
            if stats:
                self.logger.info(f"Channel stats: {stats['media_messages']} media files in last 100 messages")
            
            # Устанавливаем счетчики для контроля лимита
            files_processed = 0
            files_downloaded = 0
            
            # Последовательно обрабатываем сообщения 
            async for media_info in self.parser.parse_messages(entity):
                # Увеличиваем счетчик обработанных файлов
                files_processed += 1
                
                # Применяем фильтры
                if self.media_filter.should_process_media(media_info):
                    channel_result['files_found'] += 1
                    
                    # Формируем информацию о длительности и размере
                    file_info = ""
                    
                    # Добавляем информацию о длительности, если доступна
                    duration_str = ""
                    if media_info.get('audio_meta') and media_info['audio_meta'].get('duration'):
                        duration = media_info['audio_meta']['duration']
                        minutes = duration // 60
                        seconds = duration % 60
                        duration_str = f"[{minutes:02d}:{seconds:02d}]"
                    
                    # Добавляем информацию о размере файла
                    file_size_mb = media_info['file_size'] / (1024 * 1024)
                    size_str = f"[{file_size_mb:.1f} MB]"
                    
                    # Комбинируем информацию с пробелом между частями
                    if duration_str and size_str:
                        file_info = f"{duration_str} {size_str}"
                    else:
                        file_info = f"{duration_str}{size_str}"
                    
                    # Логируем начало скачивания - эту информацию должен отображать main.py
                    self.logger.info(f"Downloading file: {media_info['filename']} {file_info}")
                    
                    # Используем улучшенный метод download_media_file с передачей file_info
                    download_result = await self.downloader.download_media_file(media_info, file_info)
                    
                    # Обрабатываем результат скачивания без дублирования логов
                    if download_result['status'] == 'success':
                        channel_result['files_downloaded'] += 1
                        channel_result['downloaded_files'].append(download_result['file_path'])
                        files_downloaded += 1
                        # Не дублируем лог, так как он уже есть в downloader.py
                    elif download_result['status'] == 'skipped':
                        channel_result['files_skipped'] += 1
                        # Не дублируем лог, так как он уже есть в downloader.py
                    else:  # failed
                        channel_result['files_failed'] += 1
                        # Не дублируем лог, так как он уже есть в downloader.py
                    
                    # Проверяем, достигли ли мы лимита скачиваний
                    if max_files > 0 and files_downloaded >= max_files:
                        self.logger.info(f"Reached file limit ({max_files}) for channel {channel_name}")
                        break
                        
                else:
                    self.logger.info(f"→ Filtered out: {media_info['filename']}")
            
            self.logger.info(f"Channel {channel_name} completed: "
                        f"{channel_result['files_downloaded']} downloaded, "
                        f"{channel_result['files_skipped']} skipped, "
                        f"{channel_result['files_failed']} failed")
            
            return channel_result
            
        except Exception as e:
            self.logger.error(f"✗ Error processing channel {channel_name}: {e}")
            raise
    
    async def show_statistics(self):
        """Display current statistics"""
        print("\n=== Download Statistics ===")
        
        # Tracker statistics
        tracker_stats = self.file_tracker.get_statistics()
        print(f"Total processed messages: {tracker_stats['total_processed_messages']}")
        print(f"Total downloaded files: {tracker_stats['total_downloaded_files']}")
        print(f"Total blacklisted files: {tracker_stats['total_blacklisted_files']}")
        
        # Download statistics
        if self.downloader:
            download_stats = self.downloader.get_download_statistics()
            print(f"Download directory: {download_stats['download_directory']}")
            print(f"Naming template: {download_stats['naming_template']}")
        
        # Filter statistics
        filter_summary = self.media_filter.get_filter_summary()
        print(f"File types filter: {filter_summary['file_types']}")
        print(f"Format filter: {filter_summary['allowed_formats']}")
        print(f"Size filter: {filter_summary['size_range_mb']['min']}-{filter_summary['size_range_mb']['max']} MB")
        
        print("=" * 30)
    
    async def cleanup_tracker(self) -> int:
        """Clean up tracker from missing files"""
        self.logger.info("Cleaning up tracker...")
        removed_count = self.file_tracker.cleanup_missing_files()
        self.logger.info(f"Removed {removed_count} missing file entries from tracker")
        return removed_count
    
    async def close(self):
        """Close connections and cleanup"""
        if self.client:
            await self.client.disconnect()
        self.logger.info("=== Telegram Music Downloader Finished ===")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Telegram Music Downloader")
    parser.add_argument("--config", "-c", default="config.yaml", help="Config file path")
    parser.add_argument("--max-files", "-m", type=int, default=0, help="Maximum files to download (0 = unlimited)")
    parser.add_argument("--stats", "-s", action="store_true", help="Show statistics only")
    parser.add_argument("--cleanup", action="store_true", help="Clean up tracker from missing files")
    
    args = parser.parse_args()
    
    # Check if config exists
    if not Path(args.config).exists():
        print(f"❌ Config file not found: {args.config}")
        print("Create config.yaml with your Telegram credentials and channel list")
        sys.exit(1)
    
    downloader = None
    try:
        # Initialize downloader
        downloader = TelegramMusicDownloader(args.config)
        
        # Handle different modes
        if args.stats:
            # Show statistics only
            await downloader.show_statistics()
        elif args.cleanup:
            # Cleanup tracker only
            removed = await downloader.cleanup_tracker()
            print(f"Cleaned up {removed} missing file entries")
        else:
            # Normal download session
            await downloader.initialize_client()
            
            # Show initial statistics
            await downloader.show_statistics()
            
            # Run download session
            results = await downloader.run_download_session(args.max_files)
            
            # Show final results
            print(f"\n=== Session Results ===")
            print(f"Channels processed: {results['channels_processed']}")
            print(f"Files found: {results['total_files_found']}")
            print(f"Files downloaded: {results['total_files_downloaded']}")
            print(f"Files skipped: {results['total_files_skipped']}")
            print(f"Files failed: {results['total_files_failed']}")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if downloader:
            await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())