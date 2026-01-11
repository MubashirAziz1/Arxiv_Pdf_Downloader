# ArXiv PDF Downloader & Parser

A comprehensive command-line tool for automatically downloading and parsing scientific papers from arXiv with metadata storage and full PDF text extraction. Designed for materials science research but easily configurable for any arXiv category.

## 🎯 Features

- **Single Command Execution**: Download and parse papers with one terminal command
- **PDF Download & Caching**: Downloads PDFs locally with intelligent caching to avoid redundant downloads
- **Advanced PDF Parsing**: Extracts full text, tables, and figures from PDFs using Docling
- **Flexible Database Setup**: Uses PostgreSQL Docker container (recommended) or local installation - easily switchable
- **Rate Limiting**: Respects arXiv API rate limits (3-second delay between requests)
- **Retry Logic**: Robust error handling with automatic retry for failed downloads
- **Easy Configuration**: Change research category by simply editing command-line arguments
- **Customizable Search**: Support for custom date ranges and search queries
- **Portable & Maintainable**: Docker-based setup for easy deployment and maintenance

## 🏗️ Architecture

**CLI Tool + PDF Parser + Database Storage**

- Fetches papers from arXiv API
- Downloads and parses PDFs using Docling
- Stores metadata and parsed content in PostgreSQL database
- Saves PDFs to local folder (`pdf_cache/`)
- Runs via single command in terminal with flexible arguments

### Technology Stack

- **Language**: Python 3.12
- **Database**: PostgreSQL with SQLAlchemy ORM
- **PDF Parsing**: Docling (IBM Research)
- **HTTP Client**: httpx (async)
- **Configuration**: Pydantic Settings
- **Package Management**: uv

## 📋 Prerequisites

- Python 3.12+
- PostgreSQL database (Docker image recommended, or local installation)
- Docker (optional, for PostgreSQL container)
- uv package manager
- Sufficient disk space for PDFs and ML models (~2-3GB for Docling models)

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

# Install all dependencies (includes Docling and PyTorch)
uv sync
```

**Note**: First-time installation may take several minutes as it downloads ML models for PDF parsing.

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


For local installation:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE db;

# Create user
CREATE USER user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE db TO user;
```

**Note**: The database tables will be created automatically on first run. You can use either Docker or local PostgreSQL - the connection string in `.env` works for both!

## 🎮 Usage

### Quick Start

Test your setup and connection to arXiv:

```bash
# Activate virtual environment (if not already active)
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Test arXiv connection
uv run python app.py --test
```

### Running the Downloader & Parser

Download and parse papers with flexible command-line options:

```bash
# Download papers from yesterday (default: 10 papers)
uv run python app.py

# Download papers from a specific date (YYYYMMDD format)
uv run python app.py --date 20250118

# Download more papers (up to 2000 per request)
uv run python app.py --max-results 50

# Combine options
uv run python app.py --date 20250118 --max-results 100
```

This will:
1. Fetch papers from arXiv for the specified date
2. Download PDFs to `pdf_cache/` folder
3. Parse PDFs using Docling to extract text, tables, and figures
4. Store metadata and parsed content in PostgreSQL database
5. Skip already downloaded papers (intelligent caching)

### Command-Line Arguments

| Argument | Description | Default | Example |
|----------|-------------|---------|---------|
| `--date` | Target date in YYYYMMDD format | Yesterday | `--date 20250118` |
| `--max-results` | Maximum number of papers to fetch | 10 | `--max-results 50` |
| `--test` | Test arXiv connection only | - | `--test` |

### Customizing Paper Download

#### Change Research Category

Edit `.env` and modify the `ARXIV__SEARCH_CATEGORY`:

```env
ARXIV__SEARCH_CATEGORY=cs.AI  # Change to your category
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
├── app.py                     # Main CLI application (RUN THIS)
├── src/                       # Application source code
│   ├── config.py             # Configuration settings
│   ├── db/                   # Database layer
│   │   ├── base.py          # Base database setup
│   │   └── factory.py       # Database factory
│   ├── models/               # SQLAlchemy models
│   │   └── paper.py         # Paper database model
│   ├── repositories/         # Data access layer
│   │   └── paper.py         # Paper repository
│   ├── schemas/              # Pydantic schemas
│   │   └── arxiv/           # ArXiv data schemas
│   │       └── paper.py     # Paper data structure
│   └── pdf_parser/           # pdf parser data scheme
│   │       └── models.py     
│   └── services/             # Business logic
│       ├── arxiv/           # ArXiv API client
│       │   ├── client.py    # Main ArXiv client
│       │   └── factory.py   # Client factory
│       ├── pdf_parser/      # PDF parsing services
│       │   ├── docling.py   # Docling parser implementation
│       │   ├── factory.py   # Parser factory
│       │   └── parser.py    # Parser interface
│       └── metadata_fetcher.py  # Paper metadata & PDF processing
├── pdf_cache/                # Downloaded PDFs stored here
├── pyproject.toml            # Project configuration and dependencies
├── uv.lock                   # Dependency lock file
├── .env                      # Environment variables (create this)
└── README.md                 # This file
```

## 🔧 Configuration

### Quick Start Configuration

1. **Change Research Category**: Edit `ARXIV__SEARCH_CATEGORY` in `.env`
2. **Adjust Rate Limiting**: Modify `ARXIV__RATE_LIMIT_DELAY` (minimum 3.0 seconds recommended)
3. **Change PDF Storage**: Update `ARXIV__PDF_CACHE_DIR` path
4. **Control Download Volume**: Use `--max-results` flag (max 2000 per request)
5. **Switch Database**: Change `POSTGRES_DATABASE_URL` in `.env` (works with Docker or local PostgreSQL)


### Database Configuration

The tool stores comprehensive paper data including:
- arXiv ID
- Title
- Authors
- Abstract
- Publication date
- Categories
- PDF URL and local path
- **Parsed PDF content** (full text extracted by Docling)
- Parsing timestamps and status

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

## 📊 Pipeline Execution Report

After each run, the tool generates a detailed report:

```
=== DAILY ARXIV PROCESSING REPORT ===
Date: 2025-01-18
Papers fetched: 50
PDFs downloaded: 48
PDFs parsed: 45
Papers stored: 50
Processing time: 342.5s
Errors encountered: 2
=== END REPORT ===
```



## 🧪 Development

### Adding New Features

The codebase is modular and easy to extend:

- **Add new data sources**: Implement new clients in `src/services/`
- **Change data models**: Modify `src/models/paper.py`
- **Add processing logic**: Extend `src/services/metadata_fetcher.py`
- **Customize PDF parsing**: Modify `src/services/pdf_parser/docling.py`

### Running in Development Mode

```bash
# Enable debug logging
# Edit app.py and change logging.DEBUG

# Run with verbose output
uv run python app.py --date 20250118 --max-results 5
```



## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🙏 Acknowledgments

- [arXiv](https://arxiv.org/) for providing open access to scientific papers
- [Docling](https://github.com/DS4SD/docling) by IBM Research for PDF parsing capabilities
- [uv](https://github.com/astral-sh/uv) for fast Python package management

---

**Note**: This tool is designed for personal research use. Please respect arXiv's [terms of use](https://arxiv.org/help/api/user-manual) and rate limits when using this tool.