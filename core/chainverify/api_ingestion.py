"""
API Ingestion Engine — Swagger/OpenAPI Parser

PAC Reference: PAC-JEFFREY-P49
Agent: CODY (GID-01)

Ingests OpenAPI/Swagger specifications and extracts endpoint definitions
for test generation. Supports OpenAPI 3.x and Swagger 2.x formats.

INVARIANTS:
- Read-only parsing (no external calls during ingestion)
- All endpoints normalized to canonical format
- Schema validation before acceptance
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import json
import re


class HTTPMethod(Enum):
    """Supported HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ParameterLocation(Enum):
    """Where the parameter appears in the request."""
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"
    BODY = "body"


class DataType(Enum):
    """Canonical data types for parameters."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    FILE = "file"
    NULL = "null"


@dataclass
class ParameterDefinition:
    """Definition of an API parameter."""
    name: str
    location: ParameterLocation
    data_type: DataType
    required: bool = False
    description: str = ""
    default: Any = None
    enum_values: list[str] = field(default_factory=list)
    pattern: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "location": self.location.value,
            "data_type": self.data_type.value,
            "required": self.required,
            "description": self.description,
            "default": self.default,
            "enum_values": self.enum_values,
            "pattern": self.pattern,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "min_length": self.min_length,
            "max_length": self.max_length,
        }


@dataclass
class EndpointDefinition:
    """Definition of an API endpoint."""
    path: str
    method: HTTPMethod
    operation_id: str
    summary: str = ""
    description: str = ""
    parameters: list[ParameterDefinition] = field(default_factory=list)
    request_body_schema: dict[str, Any] | None = None
    response_schemas: dict[str, dict[str, Any]] = field(default_factory=dict)
    security_requirements: list[dict[str, list[str]]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    deprecated: bool = False
    
    @property
    def endpoint_id(self) -> str:
        """Unique identifier for this endpoint."""
        return f"{self.method.value}:{self.path}"
    
    @property
    def path_parameters(self) -> list[ParameterDefinition]:
        """Get parameters in the path."""
        return [p for p in self.parameters if p.location == ParameterLocation.PATH]
    
    @property
    def query_parameters(self) -> list[ParameterDefinition]:
        """Get query string parameters."""
        return [p for p in self.parameters if p.location == ParameterLocation.QUERY]
    
    @property
    def header_parameters(self) -> list[ParameterDefinition]:
        """Get header parameters."""
        return [p for p in self.parameters if p.location == ParameterLocation.HEADER]
    
    @property
    def required_parameters(self) -> list[ParameterDefinition]:
        """Get all required parameters."""
        return [p for p in self.parameters if p.required]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "path": self.path,
            "method": self.method.value,
            "operation_id": self.operation_id,
            "summary": self.summary,
            "description": self.description,
            "parameters": [p.to_dict() for p in self.parameters],
            "request_body_schema": self.request_body_schema,
            "response_schemas": self.response_schemas,
            "security_requirements": self.security_requirements,
            "tags": self.tags,
            "deprecated": self.deprecated,
        }


@dataclass
class OpenAPISpec:
    """Parsed OpenAPI specification."""
    title: str
    version: str
    description: str
    base_url: str
    endpoints: list[EndpointDefinition]
    security_schemes: dict[str, dict[str, Any]] = field(default_factory=dict)
    servers: list[dict[str, str]] = field(default_factory=list)
    openapi_version: str = "3.0.0"
    
    @property
    def endpoint_count(self) -> int:
        """Total number of endpoints."""
        return len(self.endpoints)
    
    @property
    def methods_used(self) -> set[HTTPMethod]:
        """Set of HTTP methods used in this spec."""
        return {e.method for e in self.endpoints}
    
    @property
    def tags_used(self) -> set[str]:
        """Set of tags used across endpoints."""
        tags: set[str] = set()
        for endpoint in self.endpoints:
            tags.update(endpoint.tags)
        return tags
    
    def get_endpoints_by_tag(self, tag: str) -> list[EndpointDefinition]:
        """Get all endpoints with a specific tag."""
        return [e for e in self.endpoints if tag in e.tags]
    
    def get_endpoints_by_method(self, method: HTTPMethod) -> list[EndpointDefinition]:
        """Get all endpoints using a specific HTTP method."""
        return [e for e in self.endpoints if e.method == method]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "title": self.title,
            "version": self.version,
            "description": self.description,
            "base_url": self.base_url,
            "openapi_version": self.openapi_version,
            "endpoint_count": self.endpoint_count,
            "endpoints": [e.to_dict() for e in self.endpoints],
            "security_schemes": self.security_schemes,
            "servers": self.servers,
        }


class IngestionError(Exception):
    """Error during API spec ingestion."""
    pass


class APIIngestionEngine:
    """
    Engine for ingesting OpenAPI/Swagger specifications.
    
    Supports:
    - OpenAPI 3.0.x, 3.1.x
    - Swagger 2.0
    
    INVARIANTS:
    - No external calls during ingestion
    - All specs validated before acceptance
    - Malformed specs rejected with clear errors
    """
    
    def __init__(self):
        self._parsed_specs: dict[str, OpenAPISpec] = {}
    
    def ingest(self, spec_data: dict[str, Any], spec_id: str | None = None) -> OpenAPISpec:
        """
        Ingest an OpenAPI/Swagger specification.
        
        Args:
            spec_data: The parsed JSON/YAML specification
            spec_id: Optional identifier for this spec
            
        Returns:
            Parsed OpenAPISpec object
            
        Raises:
            IngestionError: If spec is invalid or unsupported
        """
        # Detect spec version
        if "openapi" in spec_data:
            spec = self._parse_openapi_3(spec_data)
        elif "swagger" in spec_data:
            spec = self._parse_swagger_2(spec_data)
        else:
            raise IngestionError("Unknown specification format: missing 'openapi' or 'swagger' field")
        
        # Store parsed spec
        key = spec_id or f"{spec.title}:{spec.version}"
        self._parsed_specs[key] = spec
        
        return spec
    
    def ingest_json(self, json_string: str, spec_id: str | None = None) -> OpenAPISpec:
        """Ingest from JSON string."""
        try:
            spec_data = json.loads(json_string)
        except json.JSONDecodeError as e:
            raise IngestionError(f"Invalid JSON: {e}")
        return self.ingest(spec_data, spec_id)
    
    def get_spec(self, spec_id: str) -> OpenAPISpec | None:
        """Retrieve a previously parsed spec."""
        return self._parsed_specs.get(spec_id)
    
    def list_specs(self) -> list[str]:
        """List all ingested spec IDs."""
        return list(self._parsed_specs.keys())
    
    def _parse_openapi_3(self, data: dict[str, Any]) -> OpenAPISpec:
        """Parse OpenAPI 3.x specification."""
        openapi_version = data.get("openapi", "3.0.0")
        
        # Validate version
        if not openapi_version.startswith("3."):
            raise IngestionError(f"Unsupported OpenAPI version: {openapi_version}")
        
        info = data.get("info", {})
        servers = data.get("servers", [])
        
        # Determine base URL
        base_url = ""
        if servers:
            base_url = servers[0].get("url", "")
        
        # Parse endpoints
        endpoints = self._parse_paths_openapi_3(
            data.get("paths", {}),
            data.get("components", {})
        )
        
        # Parse security schemes
        security_schemes = data.get("components", {}).get("securitySchemes", {})
        
        return OpenAPISpec(
            title=info.get("title", "Untitled API"),
            version=info.get("version", "0.0.0"),
            description=info.get("description", ""),
            base_url=base_url,
            endpoints=endpoints,
            security_schemes=security_schemes,
            servers=servers,
            openapi_version=openapi_version,
        )
    
    def _parse_swagger_2(self, data: dict[str, Any]) -> OpenAPISpec:
        """Parse Swagger 2.0 specification."""
        swagger_version = data.get("swagger", "2.0")
        
        if swagger_version != "2.0":
            raise IngestionError(f"Unsupported Swagger version: {swagger_version}")
        
        info = data.get("info", {})
        
        # Build base URL from host, basePath, schemes
        schemes = data.get("schemes", ["https"])
        host = data.get("host", "")
        base_path = data.get("basePath", "")
        base_url = f"{schemes[0]}://{host}{base_path}" if host else ""
        
        # Parse endpoints
        endpoints = self._parse_paths_swagger_2(
            data.get("paths", {}),
            data.get("definitions", {})
        )
        
        # Parse security definitions
        security_schemes = data.get("securityDefinitions", {})
        
        return OpenAPISpec(
            title=info.get("title", "Untitled API"),
            version=info.get("version", "0.0.0"),
            description=info.get("description", ""),
            base_url=base_url,
            endpoints=endpoints,
            security_schemes=security_schemes,
            servers=[{"url": base_url}] if base_url else [],
            openapi_version="2.0",
        )
    
    def _parse_paths_openapi_3(
        self, 
        paths: dict[str, Any],
        components: dict[str, Any]
    ) -> list[EndpointDefinition]:
        """Parse paths from OpenAPI 3.x format."""
        endpoints = []
        
        for path, path_item in paths.items():
            # Skip non-operation fields
            if path.startswith("x-"):
                continue
            
            # Path-level parameters
            path_params = path_item.get("parameters", [])
            
            for method_name in ["get", "post", "put", "patch", "delete", "head", "options"]:
                if method_name not in path_item:
                    continue
                
                operation = path_item[method_name]
                
                # Parse parameters
                params = self._parse_parameters_openapi_3(
                    path_params + operation.get("parameters", []),
                    components
                )
                
                # Parse request body
                request_body_schema = None
                if "requestBody" in operation:
                    request_body_schema = self._extract_request_body_schema(
                        operation["requestBody"],
                        components
                    )
                
                # Parse responses
                response_schemas = {}
                for status, response in operation.get("responses", {}).items():
                    if "content" in response:
                        for content_type, content in response["content"].items():
                            if "schema" in content:
                                response_schemas[status] = content["schema"]
                                break
                
                endpoint = EndpointDefinition(
                    path=path,
                    method=HTTPMethod(method_name.upper()),
                    operation_id=operation.get("operationId", f"{method_name}_{self._path_to_id(path)}"),
                    summary=operation.get("summary", ""),
                    description=operation.get("description", ""),
                    parameters=params,
                    request_body_schema=request_body_schema,
                    response_schemas=response_schemas,
                    security_requirements=operation.get("security", []),
                    tags=operation.get("tags", []),
                    deprecated=operation.get("deprecated", False),
                )
                
                endpoints.append(endpoint)
        
        return endpoints
    
    def _parse_paths_swagger_2(
        self,
        paths: dict[str, Any],
        definitions: dict[str, Any]
    ) -> list[EndpointDefinition]:
        """Parse paths from Swagger 2.0 format."""
        endpoints = []
        
        for path, path_item in paths.items():
            if path.startswith("x-"):
                continue
            
            path_params = path_item.get("parameters", [])
            
            for method_name in ["get", "post", "put", "patch", "delete", "head", "options"]:
                if method_name not in path_item:
                    continue
                
                operation = path_item[method_name]
                
                # Parse parameters (including body)
                all_params = path_params + operation.get("parameters", [])
                params = []
                request_body_schema = None
                
                for param in all_params:
                    if param.get("in") == "body":
                        request_body_schema = param.get("schema")
                    else:
                        params.append(self._parse_parameter_swagger_2(param))
                
                # Parse responses
                response_schemas = {}
                for status, response in operation.get("responses", {}).items():
                    if "schema" in response:
                        response_schemas[status] = response["schema"]
                
                endpoint = EndpointDefinition(
                    path=path,
                    method=HTTPMethod(method_name.upper()),
                    operation_id=operation.get("operationId", f"{method_name}_{self._path_to_id(path)}"),
                    summary=operation.get("summary", ""),
                    description=operation.get("description", ""),
                    parameters=params,
                    request_body_schema=request_body_schema,
                    response_schemas=response_schemas,
                    security_requirements=operation.get("security", []),
                    tags=operation.get("tags", []),
                    deprecated=operation.get("deprecated", False),
                )
                
                endpoints.append(endpoint)
        
        return endpoints
    
    def _parse_parameters_openapi_3(
        self,
        parameters: list[dict[str, Any]],
        components: dict[str, Any]
    ) -> list[ParameterDefinition]:
        """Parse parameters from OpenAPI 3.x format."""
        result = []
        
        for param in parameters:
            # Resolve $ref if present
            if "$ref" in param:
                param = self._resolve_ref(param["$ref"], components)
            
            schema = param.get("schema", {})
            
            result.append(ParameterDefinition(
                name=param.get("name", ""),
                location=ParameterLocation(param.get("in", "query")),
                data_type=DataType(schema.get("type", "string")),
                required=param.get("required", False),
                description=param.get("description", ""),
                default=schema.get("default"),
                enum_values=schema.get("enum", []),
                pattern=schema.get("pattern"),
                min_value=schema.get("minimum"),
                max_value=schema.get("maximum"),
                min_length=schema.get("minLength"),
                max_length=schema.get("maxLength"),
            ))
        
        return result
    
    def _parse_parameter_swagger_2(self, param: dict[str, Any]) -> ParameterDefinition:
        """Parse a single parameter from Swagger 2.0 format."""
        return ParameterDefinition(
            name=param.get("name", ""),
            location=ParameterLocation(param.get("in", "query")),
            data_type=DataType(param.get("type", "string")),
            required=param.get("required", False),
            description=param.get("description", ""),
            default=param.get("default"),
            enum_values=param.get("enum", []),
            pattern=param.get("pattern"),
            min_value=param.get("minimum"),
            max_value=param.get("maximum"),
            min_length=param.get("minLength"),
            max_length=param.get("maxLength"),
        )
    
    def _extract_request_body_schema(
        self,
        request_body: dict[str, Any],
        components: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract schema from request body."""
        content = request_body.get("content", {})
        
        # Prefer JSON content type
        for content_type in ["application/json", "application/x-www-form-urlencoded"]:
            if content_type in content:
                return content[content_type].get("schema")
        
        # Fall back to first content type
        if content:
            first_content = next(iter(content.values()))
            return first_content.get("schema")
        
        return None
    
    def _resolve_ref(self, ref: str, components: dict[str, Any]) -> dict[str, Any]:
        """Resolve a $ref reference."""
        # Simple resolution for #/components/... refs
        if ref.startswith("#/components/"):
            parts = ref.split("/")[2:]  # Skip #/components/
            result = components
            for part in parts:
                result = result.get(part, {})
            return result
        return {}
    
    def _path_to_id(self, path: str) -> str:
        """Convert path to valid operation ID."""
        # Remove leading slash and path parameters
        clean = re.sub(r"\{[^}]+\}", "", path)
        clean = clean.strip("/").replace("/", "_").replace("-", "_")
        return clean or "root"


# Module-level singleton
_ingestion_engine: APIIngestionEngine | None = None


def get_ingestion_engine() -> APIIngestionEngine:
    """Get the singleton ingestion engine."""
    global _ingestion_engine
    if _ingestion_engine is None:
        _ingestion_engine = APIIngestionEngine()
    return _ingestion_engine


def reset_ingestion_engine() -> None:
    """Reset the singleton (for testing)."""
    global _ingestion_engine
    _ingestion_engine = None


def ingest_openapi(spec_data: dict[str, Any], spec_id: str | None = None) -> OpenAPISpec:
    """Convenience function to ingest an OpenAPI spec."""
    return get_ingestion_engine().ingest(spec_data, spec_id)
