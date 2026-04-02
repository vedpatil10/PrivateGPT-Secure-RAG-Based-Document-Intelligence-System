"""
Simple retrieval benchmark scaffold for local performance testing.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rag_pipeline import get_rag_pipeline


def main():
    parser = argparse.ArgumentParser(description="Benchmark PrivateGPT query latency.")
    parser.add_argument("--org-id", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--role", default="analyst")
    args = parser.parse_args()

    pipeline = get_rag_pipeline()
    started = time.perf_counter()
    result = pipeline.query(
        question=args.question,
        org_id=args.org_id,
        user_role=args.role,
    )
    elapsed = (time.perf_counter() - started) * 1000

    print(f"Measured latency: {elapsed:.1f} ms")
    print(f"Pipeline-reported latency: {result['query_time_ms']} ms")
    print(f"Chunks used: {result['chunks_used']}")
    print(result["answer"])


if __name__ == "__main__":
    main()
