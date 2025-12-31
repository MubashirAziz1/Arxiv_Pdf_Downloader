# ArXiv PDF Downloader

A comprehensive system for automatically downloading and managing scientific papers from arXiv using Apache Airflow DAGs and a FastAPI-based REST API. This project enables automated daily paper ingestion, PDF downloading, metadata extraction, and database storage to help researchers stay updated with the latest publications.

## 🎯 Features

- **Automated Daily Paper Ingestion**: Airflow DAGs automatically fetch new papers from arXiv on a scheduled basis (Monday-Friday at 6 AM UTC)
- **PDF Download & Caching**: Downloads PDFs with intelligent caching to avoid redundant downloads
- **Metadata Extraction**: Extracts and stores paper metadata (title, authors, abstract, categories, publication date)
- **REST API**: FastAPI-based API for programmatic access to paper data
- **Database Integration**: PostgreSQL database for persistent storage of paper metadata
- **Rate Limiting**: Respects arXiv API rate limits (3-second delay between requests)
- **Error Handling**: Robust error handling with retry logic for failed downloads
- **Daily Reports**: Automated daily processing reports with statistics
- **Customizable Search**: Support for custom arXiv search queries and date filtering

## 🏗️ Architecture

The project consists of two main components:

1. **FastAPI Application**: REST API for querying and managing papers
2. **Apache Airflow DAGs**: Automated workflows for daily paper ingestion

### Technology Stack

- **Backend**: FastAPI, Python 3.12
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Workflow Orchestration**: Apache Airflow
- **HTTP Client**: httpx (async)
- **PDF Processing**: Docling
- **Configuration**: Pydantic Settings
- **Package Management**: uv (via pyproject.toml)

## 📋 Prerequisites

- Python 3.12
- PostgreSQL database
- Apache Airflow (for automated ingestion)
- Docker (optional, for containerized Airflow deployment)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Arxiv_PDF_Downloader
```

### 2. Install Dependencies

The project uses `uv` for package management. Install dependencies:

```bash
# Install uv if not already installed
pip install uv

# Install project dependencies
uv sync

# Install development dependencies (optional)
uv sync --group dev
```

### 3. Environment Configuration

Create a `.env` file in the project root with the following variables:

```env
# Application Settings
APP_VERSION=0.1.0
DEBUG=true
ENVIRONMENT=development
SERVICE_NAME=arxiv-pdf-downloader

# PostgreSQL Configuration
POSTGRES_DATABASE_URL=postgresql://rag_user:rag_password@localhost:5432/rag_db
POSTGRES_ECHO_SQL=false
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=0

# ArXiv API Settings (optional, defaults provided)
ARXIV__BASE_URL=https://export.arxiv.org/api/query
ARXIV__SEARCH_CATEGORY=cs.AI
ARXIV__MAX_RESULTS=10
ARXIV__RATE_LIMIT_DELAY=3.0
ARXIV__TIMEOUT_SECONDS=30
ARXIV__PDF_CACHE_DIR=./pdf_cache
```

### 4. Database Setup

Ensure PostgreSQL is running and create the database:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE rag_db;

# Create user (if needed)
CREATE USER rag_user WITH PASSWORD 'rag_password';
GRANT ALL PRIVILEGES ON DATABASE rag_db TO rag_user;
```

Run database migrations (if using Alembic):

```bash
alembic upgrade head
```

## 🎮 Usage

### Running the FastAPI Application

Start the API server:

```bash
# From project root
python -m src.main

# Or using uvicorn directly
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

API Documentation (Swagger UI): `http://localhost:8000/docs`

### Using the Airflow DAGs

#### Setup Airflow

1. **Using Docker** (Recommended):

   The project includes a Dockerfile for Airflow. Build and run:

   ```bash
   cd airflow
   docker build -t arxiv-airflow .
   docker run -d -p 8080:8080 arxiv-airflow
   ```

2. **Local Installation**:

   Install Airflow and dependencies:

   ```bash
   pip install -r airflow/requirements-airflow.txt
   ```

   Set up Airflow:

   ```bash
   export AIRFLOW_HOME=/path/to/airflow
   airflow db init
   airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@example.com
   ```

#### Running the DAG

1. Access Airflow UI at `http://localhost:8080`
2. Login with your credentials
3. Enable the `arxiv_paper_ingestion` DAG
4. The DAG will automatically run on schedule (Monday-Friday at 6 AM UTC)

#### Manual DAG Trigger

You can also trigger the DAG manually:

```bash
airflow dags trigger arxiv_paper_ingestion
```

### DAG Workflow

The `arxiv_paper_ingestion` DAG consists of the following tasks:

1. **setup_environment**: Verifies database connection and initializes services
2. **fetch_daily_papers**: Fetches papers from arXiv for the previous day
3. **process_failed_pdfs**: Retries processing of any failed PDF downloads
4. **create_opensearch_placeholders**: Creates placeholders for OpenSearch integration (if configured)
5. **generate_daily_report**: Generates a summary report of the day's processing
6. **cleanup_temp_files**: Cleans up temporary files older than 30 days

## 📁 Project Structure

```
Arxiv_PDF_Downloader/
├── airflow/                    # Airflow DAGs and configuration
│   ├── dags/
│   │   ├── arxiv_ingestion/    # DAG task modules
│   │   │   ├── __init__.py
│   │   │   └── tasks.py        # Task implementations
│   │   ├── arxiv_paper_ingestion.py  # Main DAG definition
│   │   └── hello_world_dag.py
│   ├── Dockerfile              # Airflow container definition
│   ├── entrypoint.sh           # Airflow entrypoint script
│   └── requirements-airflow.txt # Airflow dependencies
├── src/                        # Main application source code
│   ├── config.py              # Configuration management
│   ├── database.py            # Database setup
│   ├── dependencies.py        # Dependency injection
│   ├── exceptions.py          # Custom exceptions
│   ├── main.py                # FastAPI application entry point
│   ├── db/                    # Database abstractions
│   │   ├── factory.py
│   │   └── interfaces/        # Database interface implementations
│   ├── models/                # SQLAlchemy models
│   │   └── paper.py
│   ├── repositories/          # Data access layer
│   │   └── paper.py
│   ├── routers/               # API route handlers
│   │   └── ping.py            # Health check endpoint
│   ├── schemas/               # Pydantic schemas
│   │   ├── api/               # API request/response schemas
│   │   └── arxiv/             # ArXiv data schemas
│   └── services/              # Business logic
│       ├── arxiv/             # ArXiv API client
│       │   ├── client.py      # Main ArXiv client
│       │   └── factory.py
│       └── metadata_fetcher.py # Paper metadata processing
├── pyproject.toml             # Project configuration and dependencies
├── uv.lock                    # Dependency lock file
└── README.md                  # This file
```

## 🔧 Configuration

### ArXiv API Settings

The ArXiv client can be configured via environment variables:

- `ARXIV__BASE_URL`: ArXiv API base URL (default: `https://export.arxiv.org/api/query`)
- `ARXIV__SEARCH_CATEGORY`: Default category to search (e.g., `cs.AI`, `cond-mat.mtrl-sci`)
- `ARXIV__MAX_RESULTS`: Maximum number of results per query (default: 10)
- `ARXIV__RATE_LIMIT_DELAY`: Delay between API requests in seconds (default: 3.0)
- `ARXIV__TIMEOUT_SECONDS`: Request timeout in seconds (default: 30)
- `ARXIV__PDF_CACHE_DIR`: Directory for caching downloaded PDFs

### Search Categories

Common arXiv categories:
- `cs.AI`: Artificial Intelligence
- `cs.LG`: Machine Learning
- `cs.CV`: Computer Vision
- `cond-mat.mtrl-sci`: Materials Science
- `physics`: Physics (general)

See [arXiv category taxonomy](https://arxiv.org/category_taxonomy) for a complete list.

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_arxiv_client.py
```

### Code Quality

The project uses `ruff` for linting and `mypy` for type checking:

```bash
# Lint code
ruff check src/

# Format code
ruff format src/

# Type checking
mypy src/
```

### Pre-commit Hooks

Install pre-commit hooks:

```bash
pre-commit install
```

## 📝 API Endpoints

### Health Check

- **GET** `/api/v1/ping`: Health check endpoint

More endpoints can be added by implementing routers in `src/routers/`.

## 🔍 ArXiv Client Usage

The ArXiv client provides several methods for fetching papers:

### Fetch Papers by Category

```python
from src.services.arxiv.factory import make_arxiv_client

client = make_arxiv_client()
papers = await client.fetch_papers(
    max_results=10,
    from_date="20240101",
    to_date="20240131"
)
```

### Fetch Papers with Custom Query

```python
papers = await client.fetch_papers_with_query(
    search_query="cat:cs.AI AND ti:transformer",
    max_results=20
)
```

### Fetch Specific Paper by ID

```python
paper = await client.fetch_paper_by_id("2507.17748")
```

### Download PDF

```python
pdf_path = await client.download_pdf(paper, force_download=False)
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   - Verify PostgreSQL is running
   - Check database credentials in `.env`
   - Ensure database exists and user has proper permissions

2. **ArXiv API Rate Limiting**:
   - The client automatically handles rate limiting with 3-second delays
   - If you encounter 429 errors, increase `ARXIV__RATE_LIMIT_DELAY`

3. **PDF Download Failures**:
   - Check network connectivity
   - Verify PDF URLs are accessible
   - Review logs for specific error messages
   - Failed downloads are automatically retried

4. **Airflow DAG Not Running**:
   - Verify DAG is enabled in Airflow UI
   - Check Airflow scheduler is running
   - Review DAG logs for errors
   - Ensure all dependencies are installed in Airflow environment

## 📄 License

[Add your license here]

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

[Add your contact information here]

---

**Note**: This project is designed for personal use to stay updated with arXiv papers. Please respect arXiv's [terms of use](https://arxiv.org/help/api/user-manual) and rate limits when using this tool.
