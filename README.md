# ArXiv PDF Downloader

A simple command-line tool for automatically downloading scientific papers from arXiv with metadata storage. Designed for materials science research but easily configurable for any arXiv category.

## 🎯 Features

- **Single Command Execution**: Download papers with one terminal command
- **PDF Download & Caching**: Downloads PDFs locally with intelligent caching to avoid redundant downloads
- **Metadata Storage**: PostgreSQL database for persistent storage of paper metadata (title, authors, abstract, categories, publication dates)
- **Flexible Database Setup**: Uses PostgreSQL Docker container (recommended) or local installation - easily switchable
- **Rate Limiting**: Respects arXiv API rate limits (3-second delay between requests)
- **Retry Logic**: Robust error handling with automatic retry for failed downloads
- **Easy Configuration**: Change research category by simply editing `config.py`
- **Customizable Search**: Support for custom date ranges and search queries
- **Portable & Maintainable**: Docker-based setup for easy deployment and maintenance

## 🏗️ Architecture

**Simple CLI Tool + Database Storage**

- Fetches papers from arXiv API
- Stores metadata in PostgreSQL database
- Saves PDFs to local folder (`pdf_cache/`)
- Runs via single command in terminal

### Technology Stack

- **Language**: Python 3.12
- **Database**: PostgreSQL with SQLAlchemy ORM
- **HTTP Client**: httpx (async)
- **Configuration**: Pydantic Settings
- **Package Management**: uv

## 📋 Prerequisites

- Python 3.12+
- PostgreSQL database (Docker image recommended, or local installation)
- Docker (optional, for PostgreSQL container)
- uv package manager

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Arxiv_PDF_Downloader
```

### 2. Install uv Package Manager

```bash
# Install uv if not already installed
pip install uv
```

### 3. Create Virtual Environment & Install Dependencies

```bash
# Create and activate virtual environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies
uv sync
```

### 4. Environment Configuration

Create a `.env` file in the project root:

```env
# PostgreSQL Configuration
POSTGRES_DATABASE_URL=postgresql://rag_user:rag_password@localhost:5432/rag_db
POSTGRES_ECHO_SQL=false
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=0

# ArXiv API Settings
ARXIV__BASE_URL=https://export.arxiv.org/api/query
ARXIV__SEARCH_CATEGORY=cond-mat.mtrl-sci  # Materials Science
ARXIV__MAX_RESULTS=50
ARXIV__RATE_LIMIT_DELAY=3.0
ARXIV__TIMEOUT_SECONDS=30
ARXIV__PDF_CACHE_DIR=./pdf_cache
```

### 5. Database Setup

**Option A: PostgreSQL with Docker (Recommended)**

Run PostgreSQL in a Docker container:

```bash
# Pull and run PostgreSQL Docker image
docker run -d \
  --name arxiv-postgres \
  -e POSTGRES_DB=rag_db \
  -e POSTGRES_USER=rag_user \
  -e POSTGRES_PASSWORD=rag_password \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16

# Verify it's running
docker ps | grep arxiv-postgres

# View logs (optional)
docker logs arxiv-postgres
```



**Managing Docker PostgreSQL:**
```bash
# Stop container
docker stop arxiv-postgres

# Start container
docker start arxiv-postgres

# Remove container (data persists in volume)
docker rm arxiv-postgres

# Remove container AND data
docker rm arxiv-postgres
docker volume rm pgdata
```

**Option B: Local PostgreSQL Installation**

If you prefer a local installation:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE rag_db;

# Create user
CREATE USER rag_user WITH PASSWORD 'rag_password';
GRANT ALL PRIVILEGES ON DATABASE rag_db TO rag_user;
```

**Note**: The database tables will be created automatically on first run. You can use either Docker or local PostgreSQL - the connection string in `.env` works for both!

## 🎮 Usage

### Running the Downloader

Download papers with a single command:

```bash
# Activate virtual environment (if not already active)
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run the paper ingestion
python -m src.main
```

This will:
1. Fetch papers from arXiv based on your configured category
2. Download PDFs to `pdf_cache/` folder
3. Store metadata in PostgreSQL database
4. Skip already downloaded papers (intelligent caching)

### Customizing Paper Download

#### Change Research Category

Edit `src/config.py` and modify the `search_category`:

```python
class ArxivSettings(BaseSettings):
    search_category: str = "cond-mat.mtrl-sci"  # Change this!
```

**Common arXiv Categories:**
- `cond-mat.mtrl-sci` - Materials Science (default)
- `cs.AI` - Artificial Intelligence
- `cs.LG` - Machine Learning
- `cs.CV` - Computer Vision and Pattern Recognition
- `physics.app-ph` - Applied Physics
- `cond-mat.mes-hall` - Mesoscale and Nanoscale Physics
- `cond-mat.stat-mech` - Statistical Mechanics

See [arXiv category taxonomy](https://arxiv.org/category_taxonomy) for complete list.



## 📁 Project Structure

```
Arxiv_PDF_Downloader/
├── src/                        # Main application source code
│   ├── config.py              # Configuration (EDIT THIS for category change)
│   ├── database.py            # Database setup
│   ├── dependencies.py        # Dependency injection
│   ├── exceptions.py          # Custom exceptions
│   ├── models/                # SQLAlchemy models
│   │   └── paper.py           # Paper database model
│   ├── repositories/          # Data access layer
│   │   └── paper.py           # Paper repository
│   ├── schemas/               # Pydantic schemas
│   │   └── arxiv/             # ArXiv data schemas
│   │       └── paper.py       # Paper data structure
│   └── services/              # Business logic
│       ├── arxiv/             # ArXiv API client
│       │   ├── client.py      # Main ArXiv client
│       │   └── factory.py     # Client factory
│       └── metadata_fetcher.py # Paper metadata processing
├── pdf_cache/                 # Downloaded PDFs stored here
├── pyproject.toml             # Project configuration and dependencies
├── uv.lock                    # Dependency lock file
├── .env                       # Environment variables (create this)
└── README.md                  # This file
```

## 🔧 Configuration

### Quick Start Configuration

1. **Change Research Category**: Edit `ARXIV__SEARCH_CATEGORY` in `.env` or modify `src/config.py`
2. **Adjust Rate Limiting**: Modify `ARXIV__RATE_LIMIT_DELAY` (minimum 3.0 seconds recommended)
3. **Change PDF Storage**: Update `ARXIV__PDF_CACHE_DIR` path
4. **Control Download Volume**: Set `ARXIV__MAX_RESULTS` (max 2000 per request)
5. **Switch Database**: Change `POSTGRES_DATABASE_URL` in `.env` (works with Docker or local PostgreSQL)

**Example - Switching to Different Database:**
```env
# Use different Docker container
POSTGRES_DATABASE_URL=postgresql://user:pass@localhost:5433/different_db

# Use remote PostgreSQL server
POSTGRES_DATABASE_URL=postgresql://user:pass@192.168.1.100:5432/arxiv_db
```

### Database Configuration

The tool stores paper metadata including:
- arXiv ID
- Title
- Authors
- Abstract
- Publication date
- Categories
- PDF URL and local path

All data persists in PostgreSQL for easy querying and analysis.

**PostgreSQL Flexibility:**
- **Easy to maintain**: Docker container can be stopped/started without data loss
- **Easy to modify**: Change credentials or database name by updating `.env` and recreating container
- **Easy to backup**: Use `docker exec` for database dumps or volume backups
- **Portable**: Switch between Docker and local PostgreSQL by changing connection string only

**Database Backup (Docker):**
```bash
# Backup database
docker exec arxiv-postgres pg_dump -U rag_user rag_db > backup.sql

# Restore database
docker exec -i arxiv-postgres psql -U rag_user rag_db < backup.sql
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   
   **For Docker PostgreSQL:**
   ```bash
   # Check if container is running
   docker ps | grep arxiv-postgres
   
   # Start if stopped
   docker start arxiv-postgres
   
   # Check logs for errors
   docker logs arxiv-postgres
   
   # Test connection
   docker exec -it arxiv-postgres psql -U rag_user -d rag_db
   ```
   
   **For Local PostgreSQL:**
   ```bash
   # Verify PostgreSQL is running
   sudo systemctl status postgresql  # Linux
   brew services list                # macOS
   
   # Test connection
   psql -U rag_user -d rag_db -h localhost
   ```
   
   **Common fixes:**
   - Verify credentials in `.env` match your setup
   - Ensure port 5432 is not blocked by firewall
   - Check `POSTGRES_DATABASE_URL` format is correct

2. **ArXiv API Rate Limiting (429 Error)**:
   - **Wait 30-60 minutes** if you hit rate limit
   - Increase `ARXIV__RATE_LIMIT_DELAY` to 5.0 or higher
   - Avoid running the script multiple times in quick succession
   - arXiv recommends maximum 1 request per 3 seconds



3. **uv Environment Issues**:
   ```bash
   # Recreate virtual environment
   rm -rf .venv
   uv venv
   source .venv/bin/activate
   uv sync
   ```

4. **Import Errors**:
   ```bash
   # Ensure you're in the project root directory
   # Activate virtual environment first
   source .venv/bin/activate
   python -m src.main  # Use -m flag
   ```

## 🧪 Development

### Adding New Features

The codebase is modular and easy to extend:

- **Add new data sources**: Implement new clients in `src/services/`
- **Change data models**: Modify `src/models/paper.py`
- **Add processing logic**: Extend `src/services/metadata_fetcher.py`



## 🔮 Future Enhancements

Planned features:
- [ ] Airflow DAG for scheduled automation
- [ ] FastAPI endpoints for programmatic access
- [ ] Using Docling to Parse PDF Data
- [ ] Multiple category support
- [ ] Citation analysis
- [ ] Full-text search

## 📄 License

[Add your license here]

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


**Note**: This tool is designed for personal research use. Please respect arXiv's [terms of use](https://arxiv.org/help/api/user-manual) and rate limits when using this tool.