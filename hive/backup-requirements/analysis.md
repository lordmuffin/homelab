# Backup Requirements Analysis

## Apps WITH Existing Backups
✅ **Database-backed apps (PostgreSQL)**:
- blinko
- finances/actual 
- litellm
- n8n
- paperless
- tandoor
- vikunja
- obsidian (file-based)

## Apps NEEDING Backup Implementations

### High Priority (Data-intensive)
🔴 **wallabag** - Article archiving with PostgreSQL database
🔴 **wger** - Workout tracking with PostgreSQL + Redis
🔴 **gitea** - Git repositories + PostgreSQL database  
🔴 **archivebox** - Web archiving with large file storage
🔴 **grill-stats** - Complex multi-database system (PostgreSQL, InfluxDB, Redis)

### Medium Priority (Configuration + some data)
🟡 **grocy** - Grocery management (SQLite/files)
🟡 **jellyfin** - Media metadata + configuration
🟡 **changedetection** - Website monitoring data
🟡 **homepage** - Dashboard configuration
🟡 **nitter** - Configuration + Redis cache

### Medium Priority (Media-focused)
🟡 **Media Stack** (sonarr, radarr, lidarr, prowlarr, bazarr, qbittorrent)
🟡 **MLOps Stack** (local-ai, langflow, milvus, wandb)

### Lower Priority (Stateless/Easily reproducible)
🟢 **librex** - Search proxy (minimal state)
🟢 **rss/feedpushr** - RSS feeds (mostly configuration)
🟢 **proxitok** - TikTok proxy (no persistent data)

## Infrastructure Components Needing Backups
- **Velero** cluster-level backups
- **Volume snapshots** for PVCs
- **etcd** backups for Kubernetes state
- **ArgoCD** configuration backups

## Backup Strategy Patterns
1. **PostgreSQL + B2** (existing pattern from Tandoor)
2. **File-based + B2** (for configuration and file storage)
3. **Volume snapshots** (for large data volumes)
4. **Multi-database** (for complex apps like grill-stats)