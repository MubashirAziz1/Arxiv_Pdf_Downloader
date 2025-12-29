import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dateutil import parser as date_parser
from sqlalchemy.orm import Session
from src.exceptions import MetadataFetchingException, PipelineException
from src.repositories.paper import PaperRepository
from src.schemas.arxiv.paper import ArxivPaper, PaperBase
#from src.schemas.pdf_parser.models import ArxivMetadata, ParsedPaper, PdfContent
from src.services.arxiv.client import ArxivClient
#from src.services.pdf_parser.parser import PDFParserService

logger = logging.getLogger(__name__)


class MetadataFetcher:
    """
    Service for fetching arXiv papers with PDF processing and database storage.

    This service orchestrates the complete pipeline:
    1. Fetch paper metadata from arXiv API
    2. Download PDFs with caching
    3. Parse PDFs with Docling
    4. Store complete paper data in PostgreSQL
    """

    def __init__(
        self,
        arxiv_client: ArxivClient,
        pdf_cache_dir: Optional[Path] = None,
        max_concurrent_downloads: int = 5,
    ):
        """
        Initialize metadata fetcher.

        Args:
            arxiv_client: ArxivClient instance for API calls
            pdf_cache_dir: Directory for PDF caching (uses client default if None)
            max_concurrent_downloads: Maximum concurrent PDF downloads
        """
        self.arxiv_client = arxiv_client
        self.pdf_cache_dir = pdf_cache_dir or self.arxiv_client.pdf_cache_dir
        self.max_concurrent_downloads = max_concurrent_downloads

    async def fetch_and_process_papers(
        self,
        max_results: Optional[int] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        process_pdfs: bool = True,
        store_to_db: bool = True,
        db_session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Fetch papers from arXiv, process PDFs, and store to database.

        Args:
            max_results: Maximum papers to fetch
            from_date: Filter papers from this date (YYYYMMDD)
            to_date: Filter papers to this date (YYYYMMDD)
            process_pdfs: Whether to download and parse PDFs
            store_to_db: Whether to store results in database
            db_session: Database session (required if store_to_db=True)

        Returns:
            Dictionary with processing results and statistics
        """

        results = {
            "papers_fetched": 0,
            "pdfs_downloaded": 0,
            "errors": [],
            "processing_time": 0,
        }

        start_time = datetime.now()

        try:
            # Step 1: Fetch paper metadata from arXiv
            papers = await self.arxiv_client.fetch_papers(
                max_results=max_results, from_date=from_date, to_date=to_date, sort_by="submittedDate", sort_order="descending"
            )

            results["papers_fetched"] = len(papers)

            if not papers:
                logger.warning("No papers found")
                return results

            # Step 2: Process PDFs if requested
            pdf_results = {}
            if process_pdfs:
                pdf_results = await self._process_pdfs_batch(papers)
                results["pdfs_downloaded"] = pdf_results["downloaded"]
                results["errors"].extend(pdf_results["errors"])

            # Step 3: Store to database if requested
            if store_to_db and db_session:
                logger.info("Step 3: Storing papers to database...")
                stored_count = self._store_papers_to_db(papers, pdf_results.get("parsed_papers", {}), db_session)
                results["papers_stored"] = stored_count
            elif store_to_db:
                logger.warning("Database storage requested but no session provided")
                results["errors"].append("Database session not provided for storage")

            # Calculate total processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            results["processing_time"] = processing_time

            # Simple logging summary
            logger.info(
                f"Pipeline completed in {processing_time:.1f}s: {results['papers_fetched']} papers, {results['pdfs_downloaded']} PDFs, {len(results['errors'])} errors"
            )

            if results["errors"]:
                logger.warning("Errors summary:")
                for i, error in enumerate(results["errors"][:5], 1):  # Show first 5 errors
                    logger.warning(f"  {i}. {error}")
                if len(results["errors"]) > 5:
                    logger.warning(f"  ... and {len(results['errors']) - 5} more errors")

            return results

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            results["errors"].append(f"Pipeline error: {str(e)}")
            raise PipelineException(f"Pipeline execution failed: {e}") from e

    async def _process_pdfs_batch(self, papers: List[ArxivPaper]) -> Dict[str, Any]:
        """
        Process PDFs for a batch of papers with async concurrency.

        Uses overlapping download+parse pipeline:
        - Downloads happen concurrently (up to max_concurrent_downloads)

        This is optimal for production workloads like 100 papers/day.

        Args:
            papers: List of ArxivPaper objects

        Returns:
            Dictionary with processing results and statistics
        """
        results = {
            "downloaded": 0,
            "errors": [],
            "download_failures": [],
        }

        logger.info(f"Starting async pipeline for {len(papers)} PDFs...")
        logger.info(f"Concurrent downloads: {self.max_concurrent_downloads}")

        # Create semaphores for controlled concurrency
        download_semaphore = asyncio.Semaphore(self.max_concurrent_downloads)

        # Start all download+parse pipelines concurrently
        pipeline_tasks = [self._download_and_pipeline(paper, download_semaphore) for paper in papers]

        # Wait for all pipelines to complete
        pipeline_results = await asyncio.gather(*pipeline_tasks, return_exceptions=True)

        # Process results with detailed error tracking
        for paper, result in zip(papers, pipeline_results):
            if isinstance(result, Exception):
                error_msg = f"Pipeline error for {paper.arxiv_id}: {str(result)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
            elif result:
                # Result is bool: True or False
                download_success = result

                if download_success:
                    results["downloaded"] += 1

                else:
                    # Download failed
                    results["download_failures"].append(paper.arxiv_id)
            else:
                # No result returned (shouldn't happen but handle gracefully)
                results["download_failures"].append(paper.arxiv_id)

        # Simple processing summary
        logger.info(f"PDF processing: {results['downloaded']}/{len(papers)} downloaded.")

        if results["download_failures"]:
            logger.warning(f"Download failures: {len(results['download_failures'])}")

        # Add specific failure info to general errors list for backward compatibility
        if results["download_failures"]:
            results["errors"].extend([f"Download failed: {arxiv_id}" for arxiv_id in results["download_failures"]])
       
        return results

    async def _download_and_pipeline(
        self, paper: ArxivPaper, download_semaphore: asyncio.Semaphore) -> bool:
        """
        Complete download pipeline for a single paper with true parallelism.

        Returns:
            download_success: bool
        """
        download_success = False

        try:
            # Step 1: Download PDF with download concurrency control
            async with download_semaphore:
                logger.debug(f"Starting download: {paper.arxiv_id}")
                pdf_path = await self.arxiv_client.download_pdf(paper, False)

                if pdf_path:
                    download_success = True
                    logger.debug(f"Download complete: {paper.arxiv_id}")
                else:
                    logger.error(f"Download failed: {paper.arxiv_id}")
                    return (False, None)

        except Exception as e:
            logger.error(f"Pipeline error for {paper.arxiv_id}: {e}")
            raise MetadataFetchingException(f"Pipeline error for {paper.arxiv_id}: {e}") from e

        return download_success

   

    def _store_papers_to_db(
        self,
        papers: List[ArxivPaper],
        db_session: Session,
    ) -> int:
        """
        Store papers to database with comprehensive metadata storage.

        Args:
            papers: List of ArxivPaper metadata
            db_session: Database session

        Returns:
            Number of papers stored successfully
        """
        paper_repo = PaperRepository(db_session)
        stored_count = 0

        for paper in papers:
            try:


                # Base paper data
                published_date = (
                    date_parser.parse(paper.published_date) if isinstance(paper.published_date, str) else paper.published_date
                )
                paper_data = {
                    "arxiv_id": paper.arxiv_id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "abstract": paper.abstract,
                    "categories": paper.categories,
                    "published_date": published_date,
                    "pdf_url": paper.pdf_url,
                }


                # No parsed content - just store metadata
                paper_data.update(
                    {"pdf_processed": False, "parser_metadata": {"note": "PDF processing not available or failed"}}
                )
                logger.debug(f"Storing paper {paper.arxiv_id} with metadata only")

                paper_create = PaperBase(**paper_data)
                stored_paper = paper_repo.upsert(paper_create)

                if stored_paper:
                    stored_count += 1
                    content_info = "metadata only"
                    logger.debug(f"Stored paper {paper.arxiv_id} to database ({content_info})")

            except Exception as e:
                logger.error(f"Failed to store paper {paper.arxiv_id}: {e}")

        # Commit all changes
        try:
            db_session.commit()
            logger.info(f"Committed {stored_count} papers to database with full content storage")
        except Exception as e:
            logger.error(f"Failed to commit papers to database: {e}")
            db_session.rollback()
            stored_count = 0

        return stored_count


def make_metadata_fetcher(
    arxiv_client: ArxivClient,
    pdf_cache_dir: Optional[Path] = None,
) -> MetadataFetcher:
    """
    Factory function to create MetadataFetcher instance optimized for production.

    Configured for typical production workloads (100 papers/day):
    - 5 concurrent downloads (I/O bound, can handle more)
    - Async pipeline for optimal resource utilization

    Args:
        arxiv_client: Configured ArxivClient
        pdf_cache_dir: Optional PDF cache directory

    Returns:
        MetadataFetcher instance optimized for production
    """
    return MetadataFetcher(
        arxiv_client=arxiv_client,
        pdf_cache_dir=pdf_cache_dir,
        max_concurrent_downloads=5,
        max_concurrent_parsing=1,
    )
