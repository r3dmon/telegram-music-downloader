import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Set, Optional, Any
from datetime import datetime


class FileTracker:
    def __init__(self, tracker_file: str = "./data/tracker.json"):
        self.tracker_file = Path(tracker_file)
        self.logger = logging.getLogger(__name__)
        
        # Initialize tracking data
        self.processed_messages: Set[int] = set()
        self.downloaded_files: Dict[str, Dict[str, Any]] = {}
        self.blacklisted_files: Set[int] = set()
        
        # Load existing data
        self._load_tracker_data()
        self._ensure_tracker_dir()
    
    def _ensure_tracker_dir(self) -> None:
        """Create tracker directory if it doesn't exist"""
        self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_tracker_data(self) -> None:
        """Load tracking data from JSON file"""
        if not self.tracker_file.exists():
            self.logger.info("Tracker file not found, starting fresh")
            return
        
        try:
            with open(self.tracker_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
                # Load processed message IDs
                self.processed_messages = set(data.get('processed_messages', []))
                
                # Load downloaded files info
                self.downloaded_files = data.get('downloaded_files', {})
                
                # Load blacklisted file IDs
                self.blacklisted_files = set(data.get('blacklisted_files', []))
                
                self.logger.info(f"Loaded tracker: {len(self.processed_messages)} processed, "
                               f"{len(self.downloaded_files)} downloaded, "
                               f"{len(self.blacklisted_files)} blacklisted")
                
        except Exception as e:
            self.logger.error(f"Failed to load tracker data: {e}")
            self.logger.warning("Starting with empty tracker")
    
    def _save_tracker_data(self) -> None:
        """Save tracking data to JSON file"""
        try:
            data = {
                'processed_messages': list(self.processed_messages),
                'downloaded_files': self.downloaded_files,
                'blacklisted_files': list(self.blacklisted_files),
                'last_updated': datetime.now().isoformat()
            }
            
            # Write to temporary file first
            temp_file = self.tracker_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            
            # Replace original file
            temp_file.replace(self.tracker_file)
            self.logger.debug("Tracker data saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save tracker data: {e}")
    
    def is_message_processed(self, message_id: int) -> bool:
        """Check if message was already processed"""
        return message_id in self.processed_messages
    
    def mark_message_processed(self, message_id: int) -> None:
        """Mark message as processed"""
        self.processed_messages.add(message_id)
        self._save_tracker_data()
        self.logger.debug(f"Message {message_id} marked as processed")
    
    def is_file_downloaded(self, file_hash: str) -> bool:
        """Check if file with this hash was already downloaded"""
        return file_hash in self.downloaded_files
    
    def is_file_blacklisted(self, message_id: int) -> bool:
        """Check if file is in blacklist"""
        return message_id in self.blacklisted_files
    
    def add_blacklisted_file(self, message_id: int, reason: str = "") -> None:
        """Add file to blacklist"""
        self.blacklisted_files.add(message_id)
        self._save_tracker_data()
        self.logger.info(f"File from message {message_id} blacklisted: {reason}")
    
    def remove_from_blacklist(self, message_id: int) -> None:
        """Remove file from blacklist"""
        if message_id in self.blacklisted_files:
            self.blacklisted_files.remove(message_id)
            self._save_tracker_data()
            self.logger.info(f"Message {message_id} removed from blacklist")
    
    def track_downloaded_file(self, media_info: Dict[str, Any], file_path: str) -> str:
        """Track downloaded file and return its hash"""
        file_hash = self._calculate_file_hash(file_path)
        
        # Calculate file size in MB for storage
        file_size_mb = media_info.get('file_size', 0) / (1024 * 1024)
        
        # Store file information
        self.downloaded_files[file_hash] = {
            'message_id': media_info['message_id'],
            'filename': media_info['filename'],
            'file_path': str(file_path),
            'file_size': media_info['file_size'],
            'file_size_mb': round(file_size_mb, 1),  # Округляем до 1 десятичного знака
            'mime_type': media_info['mime_type'],
            'download_date': datetime.now().isoformat(),
            'publish_date': media_info['publish_date'].isoformat() if media_info['publish_date'] else None
        }
        
        # Also mark message as processed
        self.mark_message_processed(media_info['message_id'])
        
        self._save_tracker_data()
        self.logger.info(f"File tracked: {media_info['filename']} -> {file_hash}")
        return file_hash
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return ""
    
    def get_file_info(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get information about downloaded file by hash"""
        return self.downloaded_files.get(file_hash)
    
    def get_downloaded_file_by_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        """Find downloaded file by message ID"""
        for file_hash, file_info in self.downloaded_files.items():
            if file_info['message_id'] == message_id:
                return {**file_info, 'file_hash': file_hash}
        return None
    
    def should_skip_file(self, media_info: Dict[str, Any]) -> tuple[bool, str]:
        """Check if file should be skipped (already processed or blacklisted)"""
        message_id = media_info['message_id']
        
        # Check blacklist first
        if self.is_file_blacklisted(message_id):
            return True, "File is blacklisted"
        
        # Check if message already processed
        if self.is_message_processed(message_id):
            existing_file = self.get_downloaded_file_by_message(message_id)
            if existing_file:
                file_path = Path(existing_file['file_path'])
                if file_path.exists():
                    return True, f"File already downloaded: {existing_file['file_path']}"
                else:
                    # Файл в трекере есть, но на диске отсутствует
                    self.logger.warning(f"File tracked but missing on disk: {existing_file['file_path']}")
                    return False, ""  # Разрешаем повторную загрузку
            else:
                return True, "Message already processed but no file found"
        
        return False, ""
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get tracker statistics"""
        return {
            'total_processed_messages': len(self.processed_messages),
            'total_downloaded_files': len(self.downloaded_files),
            'total_blacklisted_files': len(self.blacklisted_files),
            'tracker_file_path': str(self.tracker_file),
            'tracker_file_exists': self.tracker_file.exists(),
            'tracker_file_size': self.tracker_file.stat().st_size if self.tracker_file.exists() else 0
        }
    
    def cleanup_missing_files(self) -> int:
        """Remove entries for files that no longer exist on disk"""
        removed_count = 0
        files_to_remove = []
        
        for file_hash, file_info in self.downloaded_files.items():
            file_path = Path(file_info['file_path'])
            if not file_path.exists():
                files_to_remove.append(file_hash)
                removed_count += 1
                self.logger.info(f"Removing missing file from tracker: {file_info['filename']}")
        
        for file_hash in files_to_remove:
            del self.downloaded_files[file_hash]
        
        if removed_count > 0:
            self._save_tracker_data()
            self.logger.info(f"Cleaned up {removed_count} missing files from tracker")
        
        return removed_count


def create_file_tracker(config_loader=None) -> FileTracker:
    """Create file tracker instance"""
    if config_loader:
        # Use data directory from config
        download_dir = Path(config_loader.get_download_dir())
        tracker_file = download_dir.parent / "tracker.json"
    else:
        tracker_file = "./data/tracker.json"
    
    return FileTracker(str(tracker_file))
