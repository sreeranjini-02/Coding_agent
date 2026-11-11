import logging

from rag_engine import load_documents


# --------------------------------------------------
# LOGGING CONFIGURATION
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# MAIN INDEXING FUNCTION
# --------------------------------------------------

def main():

    logger.info("Starting knowledge base indexing...")

    try:

        total_chunks = load_documents()

        logger.info(
            "Knowledge base indexing completed."
        )

        logger.info(
            "Total indexed chunks: %s",
            total_chunks,
        )

    except Exception:

        logger.exception(
            "Knowledge base indexing failed."
        )


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    main()