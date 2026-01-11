import asyncio
import argparse
import logging
import sys
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, Tuple

# All imports at the top
from sqlalchemy import text
from src.db.factory import make_database
from src.services.arxiv.factory import make_arxiv_client
from src.services.metadata_fetcher import make_metadata_fetcher
from src.services.pdf_parser.factory import make_pdf_parser_service


# Setup logging with more detail
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detail
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'arxiv_pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_cached_services() -> Tuple[Any, Any, Any, Any]:
    """
    Get cached service instances using lru_cache for automatic memoization.

    Returns:
        Tuple of (arxiv_client, pdf_parser, database, metadata_fetcher)
    """
    logger.info("Initializing services (cached with lru_cache)")

    # Initialize core services
    arxiv_client = make_arxiv_client()
    pdf_parser = make_pdf_parser_service()
    database = make_database()

    # Create metadata fetcher with dependencies
    metadata_fetcher = make_metadata_fetcher(arxiv_client, pdf_parser)

    logger.info("All services initialized and cached with lru_cache")
    return arxiv_client, pdf_parser, database, metadata_fetcher


async def run_paper_ingestion_pipeline(
    target_date: str,
    max_results: int = 10,
    process_pdfs: bool = True,
) -> dict:
    """
    Async wrapper for the paper ingestion pipeline.

    Args:
        target_date: Date to fetch papers for (YYYYMMDD format)
        max_results: Maximum number of papers to fetch
        process_pdfs: Whether to process PDFs

    Returns:
        Dictionary with processing results
    """
    logger.info("="*70)
    logger.info(f"PIPELINE CONFIGURATION:")
    logger.info(f"  - target_date: {target_date} (format: YYYYMMDD)")
    logger.info(f"  - max_results: {max_results}")
    logger.info(f"  - process_pdfs: {process_pdfs}")
    logger.info("="*70)
    
    _arxiv_client, _pdf_parser, database, metadata_fetcher = get_cached_services()
    
    # Log metadata_fetcher configuration
    logger.info(f"Metadata Fetcher Type: {type(metadata_fetcher).__name__}")
    if hasattr(metadata_fetcher, 'category'):
        logger.info(f"Category Filter: {metadata_fetcher.category}")
    if hasattr(metadata_fetcher, 'arxiv_client'):
        logger.info(f"ArXiv Client Base URL: {metadata_fetcher.arxiv_client.base_url}")

    with database.get_session() as session:
        try:
            logger.info("\n>>> Calling fetch_and_process_papers() <<<")
            logger.info(f"Parameters being passed:")
            logger.info(f"  max_results={max_results}")
            logger.info(f"  from_date={target_date}")
            logger.info(f"  to_date={target_date}")
            logger.info(f"  process_pdfs={process_pdfs}")
            logger.info(f"  store_to_db=True")
            logger.info(f"  db_session={session}")
            
            results = await metadata_fetcher.fetch_and_process_papers(
                max_results=max_results,
                from_date=target_date,
                to_date=target_date,
                process_pdfs=process_pdfs,
                store_to_db=True,
                db_session=session,
            )
            
            logger.info("\n>>> fetch_and_process_papers() completed <<<")
            logger.info(f"Results type: {type(results)}")
            logger.info(f"Results content: {results}")
            
            return results
        except Exception as e:
            logger.error(f"\n!!! Error in paper ingestion pipeline !!!", exc_info=True)
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception message: {str(e)}")
            # Return a result dict even on error
            return {
                "papers_fetched": 0,
                "papers_stored": 0,
                "pdfs_downloaded": 0,
                "errors": [str(e)],
                "processing_time": 0,
            }


def setup_environment():
    """Setup environment and verify dependencies."""
    logger.info("Setting up environment for arXiv paper ingestion")

    try:
        # Get cached services (initialized once)
        arxiv_client, _pdf_parser, database, _metadata_fetcher = get_cached_services()

        # Test database connection
        with database.get_session() as session:
            session.execute(text("SELECT 1"))
            logger.info("Database connection verified")

        logger.info(f"arXiv client ready: {arxiv_client.base_url}")
        logger.info("PDF parser service ready (Docling models cached)")

        return {"status": "success", "message": "Environment setup completed"}

    except Exception as e:
        error_msg = f"Environment setup failed: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


def fetch_daily_papers(target_date: str = None, max_results: int = 10):
    """
    Fetch papers from arXiv.

    Args:
        target_date: Date in YYYYMMDD format (default: yesterday)
        max_results: Maximum number of papers to fetch (default: 10)

    Returns:
        Dictionary with processing results
    """
    logger.info("Starting arXiv paper fetch")

    try:
        # Calculate date range
        if target_date is None:
            target_dt = datetime.now() - timedelta(days=1)
            target_date = target_dt.strftime("%Y%m%d")

        logger.info(f"Target date for fetching: {target_date}")
        logger.info(f"Max results: {max_results}")

        # Execute paper ingestion pipeline
        results = asyncio.run(
            run_paper_ingestion_pipeline(
                target_date=target_date,
                max_results=max_results,
                process_pdfs=True,
            )
        )
        
        logger.info("="*60)
        logger.info(f"Fetch Results Summary:")
        logger.info(f"  Papers fetched: {results.get('papers_fetched', 0)}")
        logger.info(f"  PDFs downloaded: {results.get('pdfs_downloaded', 0)}")
        logger.info(f"  Papers stored: {results.get('papers_stored', 0)}")
        logger.info(f"  Errors: {len(results.get('errors', []))}")
        logger.info("="*60)

        return results

    except Exception as e:
        error_msg = f"Daily paper fetch failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg)


def process_failed_pdfs(**context):
    """
    Retry processing of PDFs that failed in the main fetch task.

    This function:
    1. Gets failed PDF list from the main task
    2. Retries processing with different settings
    3. Reports final success/failure statistics
    """
    logger.info("Processing failed PDFs")

    try:
        fetch_results = context["task_instance"].xcom_pull(task_ids="fetch_daily_papers", key="fetch_results")

        if not fetch_results or not fetch_results.get("errors"):
            logger.info("No failed PDFs to retry")
            return {"status": "skipped", "message": "No failures to retry"}

        logger.info(f"Found {len(fetch_results['errors'])} errors to investigate")

        for error in fetch_results["errors"]:
            # TODO: Implement retry logic
            logger.warning(f"Error to investigate: {error}")

        return {
            "status": "analyzed",
            "errors_logged": len(fetch_results["errors"]),
            "message": "Errors logged for investigation",
        }

    except Exception as e:
        error_msg = f"Failed PDF processing error: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


def generate_daily_report(**context):
    """
    Generate a daily processing report.

    This function:
    1. Collects results from all tasks
    2. Generates summary statistics
    3. Logs the daily report
    """
    logger.info("Generating daily processing report")

    try:
        fetch_results = context["task_instance"].xcom_pull(task_ids="fetch_daily_papers", key="fetch_results")

        failed_pdf_results = context["task_instance"].xcom_pull(task_ids="process_failed_pdfs")

        report = {
            "date": context["ds"],
            "execution_time": datetime.now().isoformat(),
            "papers": {
                "fetched": fetch_results.get("papers_fetched", 0) if fetch_results else 0,
                "pdfs_downloaded": fetch_results.get("pdfs_downloaded", 0) if fetch_results else 0,
                "pdfs_parsed": fetch_results.get("pdfs_parsed", 0) if fetch_results else 0,
                "stored": fetch_results.get("papers_stored", 0) if fetch_results else 0,
            },
            "processing": {
                "processing_time_seconds": fetch_results.get("processing_time", 0) if fetch_results else 0,
                "errors": len(fetch_results.get("errors", [])) if fetch_results else 0,
                "failed_pdf_retries": failed_pdf_results.get("errors_logged", 0) if failed_pdf_results else 0,
            },
            
        }

        logger.info("=== DAILY ARXIV PROCESSING REPORT ===")
        logger.info(f"Date: {report['date']}")
        logger.info(f"Papers fetched: {report['papers']['fetched']}")
        logger.info(f"PDFs downloaded: {report['papers']['pdfs_downloaded']}")
        logger.info(f"PDFs parsed: {report['papers']['pdfs_parsed']}")
        logger.info(f"Papers stored: {report['papers']['stored']}")
        logger.info(f"Processing time: {report['processing']['processing_time_seconds']:.1f}s")
        logger.info(f"Errors encountered: {report['processing']['errors']}")
        logger.info("=== END REPORT ===")

        return report

    except Exception as e:
        error_msg = f"Report generation failed: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)


def test_arxiv_connection():
    """Test if we can connect to arXiv and fetch any papers at all."""
    logger.info("\n" + "="*70)
    logger.info("TESTING ARXIV CONNECTION")
    logger.info("="*70)
    
    try:
        arxiv_client, _pdf_parser, _database, _metadata_fetcher = get_cached_services()
        
        # Try to fetch just 1 paper from arXiv to test connection
        logger.info("Testing arXiv API with a simple query...")
        logger.info(f"Base URL: {arxiv_client.base_url}")
        
        # Test with a very broad search that should always return results
        test_query = "cat:cs.AI"
        logger.info(f"Test query: {test_query}")
        
        papers = arxiv_client.fetch_papers_with_query(
            search_query=test_query,
            max_results=1
        )
        
        if papers and len(papers) > 0:
            logger.info(f"✓ ArXiv connection successful! Retrieved {len(papers)} paper(s)")
            logger.info(f"Sample paper: {papers[0].get('title', 'No title')}")
            return True
        else:
            logger.warning("⚠ ArXiv connection successful but no papers returned")
            return None
            
    except Exception as e:
        logger.error(f"✗ ArXiv connection test failed: {e}", exc_info=True)
        return False


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run arXiv paper ingestion pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Fetch papers from yesterday (default: 10 papers)
  python main.py --date 20240115          # Fetch papers from 2024-01-15
  python main.py --max-results 50         # Fetch 50 papers from yesterday
  python main.py --date 20240115 --max-results 50  # Fetch 50 papers from 2024-01-15
  python main.py --test                   # Test arXiv connection only
        """
    )
    parser.add_argument(
        '--date',
        type=str,
        default=None,
        help='Target date in YYYYMMDD format (default: yesterday)'
    )
    parser.add_argument(
        '--max-results',
        type=int,
        default=10,
        help='Maximum number of papers to fetch (default: 10)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run connection test only'
    )
    return parser.parse_args()


def main():
    """Main execution function."""
    # Parse arguments
    args = parse_arguments()
    
    logger.info("="*70)
    logger.info("Starting arXiv Paper Ingestion Pipeline (Standalone Mode)")
    logger.info("="*70)
    
    try:
        # Step 1: Setup environment
        logger.info("\n[STEP 1/4] Setting up environment...")
        setup_result = setup_environment()
        logger.info(f"✓ Setup complete: {setup_result['message']}\n")
        
        # If test mode, run connection test and exit
        if args.test:
            logger.info("\n[TEST MODE] Running connection test...")
            test_result = test_arxiv_connection()
            if test_result:
                logger.info("\n✓ Test passed! ArXiv API is accessible.")
                return 0
            elif test_result is None:
                logger.warning("\n⚠ Test inconclusive - check logs above")
                return 0
            else:
                logger.error("\n✗ Test failed - check logs above")
                return 1

        # Step 2: Fetch daily papers
        logger.info("[STEP 2/4] Fetching papers...")
        logger.info(f"  Command-line args: date={args.date}, max_results={args.max_results}")
        
        fetch_results = fetch_daily_papers(
            target_date=args.date,
            max_results=args.max_results
        )
        logger.info(f"✓ Papers fetched: {fetch_results.get('papers_fetched', 0)}\n")
        
        # Step 3: Process failed PDFs (mock context for standalone mode)
        logger.info("[STEP 3/4] Processing failed PDFs...")
        
        # Create proper mock for task_instance.xcom_pull
        class MockTaskInstance:
            def __init__(self, fetch_results):
                self.fetch_results = fetch_results
            
            def xcom_pull(self, task_ids=None, key=None):
                """Mock xcom_pull that returns fetch_results"""
                if task_ids == "fetch_daily_papers":
                    return self.fetch_results
                return None
        
        mock_context = {
            "task_instance": MockTaskInstance(fetch_results)
        }
        
        failed_results = process_failed_pdfs(**mock_context)
        logger.info(f"✓ Failed PDF processing: {failed_results['status']}\n")
        
        # Step 4: Generate report (mock context for standalone mode)
        logger.info("[STEP 4/4] Generating daily report...")
        
        class MockTaskInstanceForReport:
            def __init__(self, fetch_results, failed_results):
                self.fetch_results = fetch_results
                self.failed_results = failed_results
            
            def xcom_pull(self, task_ids=None, key=None):
                """Mock xcom_pull for report generation"""
                if task_ids == "fetch_daily_papers":
                    return self.fetch_results
                elif task_ids == "process_failed_pdfs":
                    return self.failed_results
                return None
        
        report_context = {
            "ds": datetime.now().strftime("%Y-%m-%d"),
            "task_instance": MockTaskInstanceForReport(fetch_results, failed_results)
        }
        
        report = generate_daily_report(**report_context)
        logger.info("✓ Report generated successfully\n")
        
        # Final summary
        logger.info("="*70)
        logger.info("Pipeline execution completed successfully!")
        logger.info(f"Total papers processed: {report['papers']['fetched']}")
        logger.info(f"Total papers stored: {report['papers']['stored']}")
        logger.info(f"Total processing time: {report['processing']['processing_time_seconds']:.1f}s")
        logger.info("="*70)
        
        return 0
        
    except Exception as e:
        logger.error("\n" + "="*70)
        logger.error(f"Pipeline execution failed: {str(e)}")
        logger.error("="*70)
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())