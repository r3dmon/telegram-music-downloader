import asyncio
import logging
import time
from typing import List, Dict, Optional, AsyncIterator
from datetime import datetime
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeFilename
from telethon.errors import RpcMcgetFailError


class MessageParser:
    def __init__(self, client, config_loader):
        self.client = client
        self.config = config_loader
        self.logger = logging.getLogger(__name__)
    
    async def get_channels_entities(self) -> List[tuple]:
        """Get entity objects for all configured channels"""
        channels = self.config.get_channels()
        entities = []
        
        for channel in channels:
            try:
                entity = await self.client.get_entity(channel)
                entities.append((channel, entity))
                self.logger.info(f"Channel entity retrieved: {channel} -> {entity.title}")
            except Exception as e:
                self.logger.error(f"Failed to get entity for {channel}: {e}")
        
        return entities
    
    async def parse_messages(self, entity, limit: Optional[int] = None) -> AsyncIterator[Dict]:
        """Parse messages from channel and extract media info"""
        file_types = self.config.get_file_types()
        timeout = self.config.get_message_timeout()
        
        try:
            message_count = 0
            async for message in self.client.iter_messages(entity, limit=limit):
                message_count += 1
                
                # Apply timeout between message processing
                if timeout > 0 and message_count > 1:
                    self.logger.debug(f"Waiting {timeout}s before processing next message...")
                    await asyncio.sleep(timeout)
                
                if not message.media:
                    continue
                
                media_info = await self._extract_media_info(message)
                if not media_info:
                    continue
                
                # Check if media type is in allowed types
                if media_info['type'] not in file_types:
                    continue
                
                self.logger.debug(f"Found media: {media_info['filename']} ({media_info['type']})")
                yield media_info
                
        except RpcMcgetFailError as e:
            self.logger.warning(f"Telegram internal issues: {e}")
            self.logger.info("Waiting 60 seconds before retry...")
            await asyncio.sleep(60)
        except Exception as e:
            self.logger.error(f"Error parsing messages from {entity.title}: {e}")
    
    async def _extract_media_info(self, message) -> Optional[Dict]:
        """Extract relevant media information from message"""
        if not hasattr(message.media, 'document'):
            return None
        
        document = message.media.document
        if not document:
            return None
        
        # Determine media type
        media_type = None
        if document.mime_type and document.mime_type.startswith('audio/'):
            media_type = 'audio'
        else:
            media_type = 'document'
        
        # Extract filename
        filename = None
        for attr in document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                filename = attr.file_name
                break
            elif isinstance(attr, DocumentAttributeAudio):
                if hasattr(attr, 'title') and attr.title:
                    filename = f"{attr.title}.{self._get_extension_from_mime(document.mime_type)}"
        
        # If no filename found, generate one
        if not filename:
            ext = self._get_extension_from_mime(document.mime_type)
            filename = f"file_{message.id}.{ext}"
        
        # Extract audio metadata (if available)
        audio_meta = None
        for attr in document.attributes:
            if isinstance(attr, DocumentAttributeAudio):
                audio_meta = {
                    'duration': getattr(attr, 'duration', None),
                    'title': getattr(attr, 'title', None),
                    'performer': getattr(attr, 'performer', None)
                }
                break
        
        return {
            'message_id': message.id,
            'filename': filename,
            'file_size': document.size,
            'mime_type': document.mime_type,
            'type': media_type,
            'publish_date': message.date,
            'download_date': None,  # Will be set when downloaded
            'audio_meta': audio_meta,
            'document_id': document.id,
            'access_hash': document.access_hash,
            'file_reference': document.file_reference
        }
    
    def _get_extension_from_mime(self, mime_type: str) -> str:
        """Get file extension from MIME type"""
        mime_map = {
            'audio/flac': 'flac',
            'audio/wav': 'wav',
            'audio/x-wav': 'wav',
            'audio/aiff': 'aiff',
            'audio/x-aiff': 'aiff',
            'audio/mp4': 'm4a',
            'audio/m4a': 'm4a',
            'audio/x-m4a': 'm4a',
            'audio/mpeg': 'mp3',
            'audio/mp3': 'mp3',
        }
        
        return mime_map.get(mime_type, 'bin')
    
    async def get_channel_stats(self, entity) -> Dict:
        """Get basic statistics about channel"""
        try:
            total_messages = 0
            media_messages = 0
            audio_files = 0
            document_files = 0
            
            # Sample first 100 messages for stats
            async for message in self.client.iter_messages(entity, limit=100):
                total_messages += 1
                
                if message.media and hasattr(message.media, 'document'):
                    media_messages += 1
                    document = message.media.document
                    
                    if document.mime_type and document.mime_type.startswith('audio/'):
                        audio_files += 1
                    else:
                        document_files += 1
            
            return {
                'total_messages_sampled': total_messages,
                'media_messages': media_messages,
                'audio_files': audio_files,
                'document_files': document_files,
                'media_percentage': (media_messages / total_messages * 100) if total_messages > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting channel stats: {e}")
            return {}


def create_message_parser(client, config_loader) -> MessageParser:
    """Create message parser instance"""
    return MessageParser(client, config_loader)