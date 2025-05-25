# Changelog

All notable changes to the Telegram AI Assistant project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-05-25

### Added
- **Proactive Messaging System**: Universal scheduler with per-user timezone support
  - Morning (10:00) and evening (20:00) messages in user's local time
  - Support for 6 active users across Asia/Makassar and Europe/Moscow timezones
  - Deduplication via proactive_meta collection to prevent duplicate messages
  - Enhanced logging with emoji indicators for better debugging

- **Conversation Management**: Automatic history rotation and summarization
  - Configurable threshold: 50 messages (25 user-assistant pairs) triggers summarization
  - Summarizes 30 oldest messages using Gemini 2.5 Pro
  - Maintains maximum 5 summaries per user with FIFO cleanup
  - Seamless context integration for OpenAI conversations

- **Security & Authentication**: Service identity implementation
  - Google Cloud best practices with dedicated service account
  - Cross-project authentication (Cloud Run → Firebase)
  - Removed explicit credentials from environment variables
  - Service account: therapist-o3-service@therapist-o3.iam.gserviceaccount.com

- **Resilience & Monitoring**: Comprehensive error handling
  - Error middleware with structured logging for Cloud Run
  - Retry mechanisms with exponential backoff for all API calls
  - Robust error handling for Telegram, OpenAI, and Firebase operations

- **Deployment Infrastructure**: Dual-service architecture
  - Cloud Run project (therapist-o3) for compute resources
  - Firebase project (ales-f75a1) for data storage
  - Automated build and deployment scripts
  - Environment variable management via gcloud CLI

### Changed
- Migrated from explicit credentials to service identity authentication
- Updated conversation context to include summarized history
- Enhanced logging format for better Cloud Run integration

### Security
- Implemented service identity for secure cross-project access
- Removed hardcoded credentials from environment variables
- Added dedicated service account with minimal required permissions

### Technical Details
- **Deployment**: Cloud Run service in us-central1 region
- **Current Revision**: therapist-o3-00023-8c6
- **Service URL**: https://therapist-o3-6pn7uvzyqa-uc.a.run.app
- **Git Commit**: a90771f 