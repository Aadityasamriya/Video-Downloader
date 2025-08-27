# Overview

A Telegram bot application for downloading videos and files from multiple platforms using yt-dlp. The bot supports major platforms like YouTube, Instagram, Twitter/X, TikTok, Facebook, Reddit, Pinterest, and Terabox. Users can send video links to the bot and receive downloaded content directly through Telegram.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework
- **Telegram Bot API**: Uses python-telegram-bot library for handling Telegram interactions
- **Async/Await Pattern**: Implements asynchronous programming for handling multiple concurrent downloads
- **Command Handler System**: Structured command handling with separate handlers for different bot commands

## Download Engine
- **yt-dlp Integration**: Core download functionality powered by yt-dlp, supporting 1000+ platforms
- **Threading Model**: Uses ThreadPoolExecutor for non-blocking download operations
- **Progress Tracking**: Real-time download progress callbacks with 10% increment updates
- **Format Selection**: Automatic best quality selection within file size constraints

## File Management
- **Temporary Storage**: Local filesystem with configurable temp directory for download staging
- **File Size Limits**: 50MB for Telegram uploads, 500MB max download size
- **Cleanup System**: Automatic temporary file cleanup after processing
- **Filename Sanitization**: Safe filename generation to prevent filesystem issues

## Rate Limiting & User Management
- **Request Rate Limiting**: Per-user rate limiting (5 requests per 60-second window)
- **User Statistics**: Basic user interaction tracking and statistics
- **Active Download Tracking**: Prevents duplicate downloads per user
- **Timeout Handling**: 5-minute timeout for download operations

## Error Handling & Logging
- **Comprehensive Logging**: File and console logging with structured format
- **Graceful Error Recovery**: Proper error handling for network issues, file size limits, and unsupported content
- **Validation Layer**: URL validation before processing download requests

# External Dependencies

## Core Libraries
- **python-telegram-bot**: Telegram Bot API wrapper for Python
- **yt-dlp**: Universal video/audio downloader supporting 1000+ sites
- **validators**: URL validation library

## System Requirements
- **Python 3.7+**: Modern Python runtime with async/await support
- **File System Access**: Local storage for temporary file handling
- **Network Access**: Internet connectivity for downloading content and Telegram API communication

## Configuration
- **Environment Variables**: Bot token configuration via environment variables
- **Telegram Bot Token**: Required authentication token from BotFather
- **Platform Support**: Extensible platform support through yt-dlp's plugin system