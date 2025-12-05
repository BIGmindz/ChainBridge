"""
Writer for ChainBridge event ingestion.
Appends events to Parquet and inserts into Postgres feature store.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import create_engine
from .config import PARQUET_PATH, POSTGRES_URI
import logging

logger = logging.getLogger("maggie.ingestion.writer")
engine = create_engine(POSTGRES_URI)

# Append event to Parquet file
def write_event(event):
    df = pd.DataFrame([event])
    table = pa.Table.from_pandas(df)
    pq.write_to_dataset(table, root_path=PARQUET_PATH, partition_cols=["event_type"])
    # Insert into Postgres feature store
    df.to_sql("features", engine, if_exists="append", index=False)
    logger.info(f"Event written: {event['event_id']}")
