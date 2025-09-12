"""
Benson REST API Server

FastAPI-based REST API for Benson modular architecture.
Provides endpoints for module interaction, pipeline execution, and system management.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import uvicorn
from datetime import datetime, timezone
import os

# Import core components
from core.module_manager import ModuleManager, Module
from core.data_processor import DataProcessor
from core.pipeline import Pipeline
from tracking.metrics_collector import MetricsCollector


# Pydantic models for API
class ModuleExecutionRequest(BaseModel):
    module_name: str = Field(..., description="Name of the module to execute")
    input_data: Dict[str, Any] = Field(..., description="Input data for the module")


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

# Create FastAPI app
app = FastAPI(
    title="Benson API",
    description="Multi-Signal Decision Bot Modular Architecture API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        modules_loaded=len(module_manager.list_modules()),
        active_pipelines=len(pipelines)
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
            "module_name": module_name
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
        metrics_collector.track_module_execution(
            module_name, 
            execution_time, 
            len(str(request.input_data)),
            len(str(result))
        )
        
        return {
            "result": result,
            "metadata": {
                "module_name": module_name,
                "execution_time_seconds": execution_time,
                "timestamp": start_time.isoformat()
            }
        }
        
    except Exception as e:
        metrics_collector.track_error("module_execution", module_name, str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/pipelines", response_model=List[str])
async def list_pipelines():
    """List all available pipelines."""
    return list(pipelines.keys())


@app.post("/pipelines", response_model=Dict[str, str])
async def create_pipeline(request: PipelineCreationRequest):
    """Create a new pipeline."""
    try:
        if request.pipeline_name in pipelines:
            raise HTTPException(
                status_code=400, 
                detail=f"Pipeline '{request.pipeline_name}' already exists"
            )
            
        pipeline = Pipeline(request.pipeline_name, module_manager)
        
        # Add steps to the pipeline
        for step in request.steps:
            pipeline.add_step(
                step.get('name'),
                step.get('module_name'),
                step.get('config', {})
            )
            
        # Validate the pipeline
        validation = pipeline.validate_pipeline()
        if not validation['valid']:
            raise HTTPException(
                status_code=400,
                detail=f"Pipeline validation failed: {validation['issues']}"
            )
            
        pipelines[request.pipeline_name] = pipeline
        metrics_collector.track_pipeline_creation(request.pipeline_name, len(request.steps))
        
        return {
            "message": f"Pipeline '{request.pipeline_name}' created successfully",
            "pipeline_name": request.pipeline_name
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
        "pipeline_info": pipeline.to_dict(),
        "schema": pipeline.get_pipeline_schema(),
        "performance_metrics": pipeline.get_performance_metrics()
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
        metrics_collector.track_pipeline_execution(
            pipeline_name,
            execution_time,
            len(pipeline.steps),
            True
        )
        
        return {
            "result": result,
            "metadata": {
                "pipeline_name": pipeline_name,
                "execution_time_seconds": execution_time,
                "timestamp": start_time.isoformat(),
                "steps_executed": len(pipeline.steps)
            }
        }
        
    except Exception as e:
        metrics_collector.track_pipeline_execution(
            pipeline_name,
            0,
            len(pipeline.steps) if pipeline_name in pipelines else 0,
            False
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
        data_type = data.get('data_type', 'generic')
        data_records = data.get('data', [])
        
        if not isinstance(data_records, list):
            data_records = [data_records]
            
        result = data_processor.process_batch(data_records, data_type)
        
        return {
            "processed_data": result,
            "processor_stats": data_processor.get_statistics()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Load default modules on startup
@app.on_event("startup")
async def startup_event():
    """Initialize default modules and pipelines."""
    try:
        # Register built-in modules
        module_manager.load_module("modules.csv_ingestion")
        module_manager.load_module("modules.rsi_module")
        module_manager.load_module("modules.sales_forecasting")
        
        print("Benson API server started successfully")
        print(f"Loaded {len(module_manager.list_modules())} modules")
        
    except Exception as e:
        print(f"Warning: Failed to load some modules during startup: {e}")


if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "api.server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )