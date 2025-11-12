"""
Benson REST API Server

FastAPI-based REST API for Benson modular architecture.
Provides endpoints for module interaction, pipeline execution, and system management.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.data_processor import DataProcessor

# Import core components
from core.module_manager import ModuleManager
from core.pipeline import Pipeline
from tracking.metrics_collector import MetricsCollector


# Default module configuration
DEFAULT_MODULE_IMPORTS = {
    "modules.csv_ingestion": "CSVIngestionModule",
    "modules.rsi_module": "RSIModule",
    "modules.sales_forecasting": "SalesForecastingModule",
    "modules.macd_module": "MACDModule",
    "modules.bollinger_bands_module": "BollingerBandsModule",
    "modules.volume_profile_module": "VolumeProfileModule",
    "modules.sentiment_analysis_module": "SentimentAnalysisModule",
    "modules.multi_signal_aggregator_module": "MultiSignalAggregatorModule",
}

DEFAULT_SIGNAL_MODULES = [
    "RSIModule",
    "MACDModule",
    "BollingerBandsModule",
    "VolumeProfileModule",
    "SentimentAnalysisModule",
]


# Pydantic models for API
class ModuleExecutionRequest(BaseModel):
    module_name: str = Field(..., description="Name of the module to execute")
    input_data: Dict[str, Any] = Field(..., description="Input data for the module")


class MultiSignalAnalysisRequest(BaseModel):
    price_data: List[Dict[str, Any]] = Field(..., description="Historical price data for analysis")
    signal_modules: Optional[List[str]] = Field(None, description="List of signal modules to use (default: all)")
    signal_weights: Optional[Dict[str, float]] = Field(None, description="Custom weights for each signal")
    include_individual_signals: bool = Field(True, description="Include individual signal results")


class MultiSignalBacktestRequest(BaseModel):
    historical_data: List[Dict[str, Any]] = Field(..., description="Historical price data for backtesting")
    initial_balance: float = Field(10000, description="Starting balance for backtesting")
    signal_modules: Optional[List[str]] = Field(None, description="List of signal modules to use")


class PipelineExecutionRequest(BaseModel):
    pipeline_name: str = Field(..., description="Name of the pipeline to execute")
    input_data: Dict[str, Any] = Field(..., description="Input data for the pipeline")


class ModuleRegistrationRequest(BaseModel):
    module_name: str = Field(..., description="Name to register the module as")
    module_path: str = Field(..., description="Python import path to the module")
    config: Optional[Dict[str, Any]] = Field(None, description="Configuration for the module")


class PipelineCreationRequest(BaseModel):
    pipeline_name: str = Field(..., description="Name of the new pipeline")
    steps: List[Dict[str, Any]] = Field(..., description="List of pipeline steps")


class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "1.0.0"
    modules_loaded: int
    active_pipelines: int


# Global instances
module_manager = ModuleManager()
pipelines: Dict[str, Pipeline] = {}
metrics_collector = MetricsCollector()
data_processor = DataProcessor()


def ensure_default_modules_loaded() -> List[str]:
    """Ensure that built-in modules are available for execution."""
    newly_loaded: List[str] = []

    for module_path, module_name in DEFAULT_MODULE_IMPORTS.items():
        if module_manager.get_module(module_name):
            continue

        try:
            loaded_name = module_manager.load_module(module_path)
            newly_loaded.append(loaded_name)  # type: ignore
        except Exception as exc:  # pragma: no cover - logging safeguard
            print(f"Warning: Failed to load module {module_path}: {exc}")

    return newly_loaded


# Pre-load default modules when the API module is imported so that
# endpoints that execute modules immediately have them available.
ensure_default_modules_loaded()

# Create FastAPI app
app = FastAPI(
    title="Benson API",
    description="Multi-Signal Decision Bot Modular Architecture API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with basic API information."""
    return {
        "message": "Benson Multi-Signal Decision Bot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        modules_loaded=len(module_manager.list_modules()),
        active_pipelines=len(pipelines),
    )


@app.get("/modules", response_model=List[str])
async def list_modules():
    """List all registered modules."""
    return module_manager.list_modules()


@app.get("/modules/{module_name}", response_model=Dict[str, Any])
async def get_module_info(module_name: str):
    """Get information about a specific module."""
    info = module_manager.get_module_info(module_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found")
    return info


@app.post("/modules/register", response_model=Dict[str, str])
async def register_module(request: ModuleRegistrationRequest):
    """Register a new module."""
    try:
        module_name = module_manager.load_module(request.module_path, request.config)
        metrics_collector.track_module_registration(module_name, request.module_path)
        return {
            "message": f"Module '{module_name}' registered successfully",
            "module_name": module_name,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/modules/{module_name}/execute", response_model=Dict[str, Any])
async def execute_module(module_name: str, request: ModuleExecutionRequest):
    """Execute a specific module."""
    try:
        # Track the execution
        start_time = datetime.now(timezone.utc)

        result = module_manager.execute_module(module_name, request.input_data)

        # Track metrics
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        metrics_collector.track_module_execution(module_name, execution_time, len(str(request.input_data)), len(str(result)))

        return {
            "result": result,
            "metadata": {
                "module_name": module_name,
                "execution_time_seconds": execution_time,
                "timestamp": start_time.isoformat(),
            },
        }

    except Exception as e:
        metrics_collector.track_error("module_execution", module_name, str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/pipelines", response_model=List[str])
async def list_pipelines():
    """List all available pipelines."""
    return list(pipelines.keys())  # type: ignore


@app.post("/pipelines", response_model=Dict[str, str])
async def create_pipeline(request: PipelineCreationRequest):
    """Create a new pipeline."""
    try:
        if request.pipeline_name in pipelines:
            raise HTTPException(
                status_code=400,
                detail=f"Pipeline '{request.pipeline_name}' already exists",
            )

        pipeline = Pipeline(request.pipeline_name, module_manager)

        # Add steps to the pipeline
        for step in request.steps:
            pipeline.add_step(step.get("name"), step.get("module_name"), step.get("config", {}))

        # Validate the pipeline
        validation = pipeline.validate_pipeline()
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Pipeline validation failed: {validation['issues']}",
            )

        pipelines[request.pipeline_name] = pipeline
        metrics_collector.track_pipeline_creation(request.pipeline_name, len(request.steps))

        return {
            "message": f"Pipeline '{request.pipeline_name}' created successfully",
            "pipeline_name": request.pipeline_name,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/pipelines/{pipeline_name}", response_model=Dict[str, Any])
async def get_pipeline_info(pipeline_name: str):
    """Get information about a specific pipeline."""
    if pipeline_name not in pipelines:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")

    pipeline = pipelines[pipeline_name]
    return {
        "pipeline_info": pipeline.to_dict(),  # type: ignore
        "schema": pipeline.get_pipeline_schema(),
        "performance_metrics": pipeline.get_performance_metrics(),
    }


@app.post("/pipelines/{pipeline_name}/execute", response_model=Dict[str, Any])
async def execute_pipeline(pipeline_name: str, request: PipelineExecutionRequest):
    """Execute a specific pipeline."""
    if pipeline_name not in pipelines:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")

    try:
        pipeline = pipelines[pipeline_name]
        start_time = datetime.now(timezone.utc)

        result = pipeline.execute(request.input_data)

        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        metrics_collector.track_pipeline_execution(pipeline_name, execution_time, len(pipeline.steps), True)

        return {
            "result": result,
            "metadata": {
                "pipeline_name": pipeline_name,
                "execution_time_seconds": execution_time,
                "timestamp": start_time.isoformat(),
                "steps_executed": len(pipeline.steps),
            },
        }

    except Exception as e:
        metrics_collector.track_pipeline_execution(
            pipeline_name,
            0,
            len(pipeline.steps) if pipeline_name in pipelines else 0,
            False,
        )
        metrics_collector.track_error("pipeline_execution", pipeline_name, str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/metrics", response_model=Dict[str, Any])
async def get_metrics():
    """Get system and usage metrics."""
    return metrics_collector.get_all_metrics()


@app.get("/metrics/modules", response_model=Dict[str, Any])
async def get_module_metrics():
    """Get module-specific metrics."""
    return metrics_collector.get_module_metrics()


@app.get("/metrics/pipelines", response_model=Dict[str, Any])
async def get_pipeline_metrics():
    """Get pipeline-specific metrics."""
    return metrics_collector.get_pipeline_metrics()


@app.post("/data/process", response_model=Dict[str, Any])
async def process_data(data: Dict[str, Any]):
    """Process data using the core data processor."""
    try:
        # Determine data type from input
        data_type = data.get("data_type", "generic")
        data_records = data.get("data", [])

        if not isinstance(data_records, list):
            data_records = [data_records]

        result = data_processor.process_batch(data_records, data_type)

        return {
            "processed_data": result,
            "processor_stats": data_processor.get_statistics(),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/analysis/multi-signal", response_model=Dict[str, Any])
async def multi_signal_analysis(request: MultiSignalAnalysisRequest):
    """
    Perform multi-signal analysis using all available signal modules.
    """
    try:
        start_time = datetime.now(timezone.utc)

        # Define default signal modules
        signal_modules = request.signal_modules or DEFAULT_SIGNAL_MODULES

        # Execute individual signal analyses
        individual_signals = {}

        for module_name in signal_modules:
            try:
                if module_name == "SentimentAnalysisModule":
                    # Sentiment analysis doesn't need price data
                    result = module_manager.execute_module(module_name, {})
                else:
                    # Other modules need price data
                    result = module_manager.execute_module(module_name, {"price_data": request.price_data})

                individual_signals[module_name.replace("Module", "")] = result

            except Exception as e:
                print(f"Warning: Failed to execute {module_name}: {e}")
                continue

        if not individual_signals:
            raise HTTPException(status_code=400, detail="No signal modules executed successfully")

        # Execute multi-signal aggregation
        aggregation_input = {
            "signals": individual_signals,
            "price_data": request.price_data[-1] if request.price_data else {},
        }

        if request.signal_weights:
            aggregation_input["signal_weights"] = request.signal_weights

        aggregated_result = module_manager.execute_module("MultiSignalAggregatorModule", aggregation_input)

        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Track metrics
        metrics_collector.track_business_impact("multi_signal_analysis", 1.0)

        response = {
            "aggregated_result": aggregated_result,
            "metadata": {
                "execution_time_seconds": execution_time,
                "timestamp": start_time.isoformat(),
                "signals_analyzed": len(individual_signals),
                "modules_used": list(individual_signals.keys()),  # type: ignore
            },
        }

        if request.include_individual_signals:
            response["individual_signals"] = individual_signals

        return response

    except HTTPException:
        raise
    except Exception as e:
        metrics_collector.track_error("multi_signal_analysis", "system", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/analysis/multi-signal/backtest", response_model=Dict[str, Any])
async def multi_signal_backtest(request: MultiSignalBacktestRequest):
    """
    Perform backtesting using multi-signal strategy.
    """
    try:
        start_time = datetime.now(timezone.utc)

        # Define default signal modules
        signal_modules = request.signal_modules or DEFAULT_SIGNAL_MODULES

        # Generate signal history for each period
        signal_history = {module.replace("Module", ""): [] for module in signal_modules}

        # Process each time period
        min_periods = 60  # Minimum periods needed for all indicators

        for i in range(min_periods, len(request.historical_data)):
            window_data = request.historical_data[: i + 1]

            for module_name in signal_modules:
                try:
                    if module_name == "SentimentAnalysisModule":
                        # Use mock sentiment data for backtesting
                        result = module_manager.execute_module(module_name, {})
                    else:
                        result = module_manager.execute_module(module_name, {"price_data": window_data})

                    signal_history[module_name.replace("Module", "")].append(result)  # type: ignore

                except Exception as e:
                    # Use neutral signal if module fails
                    signal_history[module_name.replace("Module", "")].append({"signal": "HOLD", "confidence": 0.0, "error": str(e)})  # type: ignore

        # Execute backtesting using multi-signal aggregator
        aggregator = module_manager.get_module("MultiSignalAggregatorModule")

        backtest_result = aggregator.backtest_multi_signal_strategy(
            request.historical_data[min_periods:],
            signal_history,
            request.initial_balance,
        )

        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Track metrics
        metrics_collector.track_business_impact("multi_signal_backtest", 1.0)

        return {
            "backtest_result": backtest_result,
            "metadata": {
                "execution_time_seconds": execution_time,
                "timestamp": start_time.isoformat(),
                "periods_analyzed": len(request.historical_data) - min_periods,
                "modules_used": signal_modules,
                "initial_balance": request.initial_balance,
            },
        }

    except Exception as e:
        metrics_collector.track_error("multi_signal_backtest", "system", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/signals/available", response_model=List[Dict[str, Any]])
async def get_available_signals():
    """
    Get information about all available signal modules.
    """
    try:
        signal_modules = DEFAULT_SIGNAL_MODULES

        available_signals = []

        for module_name in signal_modules:
            try:
                info = module_manager.get_module_info(module_name)
                if info:
                    available_signals.append(  # type: ignore
                        {
                            "module_name": module_name,
                            "display_name": module_name.replace("Module", ""),
                            "version": info.get("version", "1.0.0"),
                            "signal_type": info.get("schema", {}).get("metadata", {}).get("signal_type", "unknown"),
                            "schema": info.get("schema", {}),
                            "available": True,
                        }
                    )
            except Exception as e:
                available_signals.append(  # type: ignore
                    {
                        "module_name": module_name,
                        "display_name": module_name.replace("Module", ""),
                        "available": False,
                        "error": str(e),
                    }
                )

        return available_signals

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Load default modules on startup
@app.on_event("startup")
async def startup_event():
    """Initialize default modules and pipelines."""
    try:
        newly_loaded = ensure_default_modules_loaded()

        print("Benson API server started successfully")
        print(f"Loaded {len(module_manager.list_modules())} modules")
        if newly_loaded:
            print(f"Newly available modules: {', '.join(newly_loaded)}")
        print(f"Available modules: {', '.join(module_manager.list_modules())}")

    except Exception as e:
        print(f"Warning: Failed to load some modules during startup: {e}")


if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run("api.server:app", host=host, port=port, reload=True, log_level="info")
