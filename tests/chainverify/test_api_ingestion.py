"""
ChainVerify Tests — API Ingestion Engine

PAC Reference: PAC-JEFFREY-P49
"""

import pytest

from core.chainverify.api_ingestion import (
    APIIngestionEngine,
    OpenAPISpec,
    EndpointDefinition,
    ParameterDefinition,
    HTTPMethod,
    ParameterLocation,
    DataType,
    IngestionError,
    get_ingestion_engine,
    reset_ingestion_engine,
    ingest_openapi,
)


# Sample OpenAPI 3.0 spec
SAMPLE_OPENAPI_3 = {
    "openapi": "3.0.0",
    "info": {
        "title": "Sample API",
        "version": "1.0.0",
        "description": "A sample API for testing"
    },
    "servers": [
        {"url": "https://api.example.com/v1"}
    ],
    "paths": {
        "/users": {
            "get": {
                "operationId": "listUsers",
                "summary": "List all users",
                "tags": ["users"],
                "parameters": [
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer"},
                        "required": False
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {"type": "array"}
                            }
                        }
                    }
                }
            },
            "post": {
                "operationId": "createUser",
                "summary": "Create a user",
                "tags": ["users"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "201": {"description": "Created"}
                }
            }
        },
        "/users/{id}": {
            "get": {
                "operationId": "getUser",
                "summary": "Get a user",
                "tags": ["users"],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "schema": {"type": "string"},
                        "required": True
                    }
                ],
                "responses": {
                    "200": {"description": "Success"}
                }
            }
        }
    }
}


# Sample Swagger 2.0 spec
SAMPLE_SWAGGER_2 = {
    "swagger": "2.0",
    "info": {
        "title": "Legacy API",
        "version": "2.0.0"
    },
    "host": "api.legacy.com",
    "basePath": "/api",
    "schemes": ["https"],
    "paths": {
        "/items": {
            "get": {
                "operationId": "getItems",
                "summary": "Get items",
                "responses": {
                    "200": {"description": "OK"}
                }
            }
        }
    }
}


class TestHTTPMethod:
    """Test HTTP method enumeration."""
    
    def test_all_methods_defined(self):
        expected = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        actual = {m.value for m in HTTPMethod}
        assert actual == expected


class TestParameterLocation:
    """Test parameter location enumeration."""
    
    def test_all_locations_defined(self):
        expected = {"path", "query", "header", "cookie", "body"}
        actual = {l.value for l in ParameterLocation}
        assert actual == expected


class TestDataType:
    """Test data type enumeration."""
    
    def test_all_types_defined(self):
        expected = {"string", "integer", "number", "boolean", "array", "object", "file", "null"}
        actual = {t.value for t in DataType}
        assert actual == expected


class TestParameterDefinition:
    """Test parameter definition dataclass."""
    
    def test_create_parameter(self):
        param = ParameterDefinition(
            name="limit",
            location=ParameterLocation.QUERY,
            data_type=DataType.INTEGER,
            required=False,
            description="Max results"
        )
        
        assert param.name == "limit"
        assert param.location == ParameterLocation.QUERY
        assert param.data_type == DataType.INTEGER
        assert not param.required
    
    def test_to_dict(self):
        param = ParameterDefinition(
            name="id",
            location=ParameterLocation.PATH,
            data_type=DataType.STRING,
            required=True
        )
        
        d = param.to_dict()
        assert d["name"] == "id"
        assert d["location"] == "path"
        assert d["data_type"] == "string"
        assert d["required"] is True


class TestEndpointDefinition:
    """Test endpoint definition dataclass."""
    
    def test_create_endpoint(self):
        endpoint = EndpointDefinition(
            path="/users",
            method=HTTPMethod.GET,
            operation_id="listUsers",
            summary="List users"
        )
        
        assert endpoint.path == "/users"
        assert endpoint.method == HTTPMethod.GET
        assert endpoint.endpoint_id == "GET:/users"
    
    def test_parameter_accessors(self):
        endpoint = EndpointDefinition(
            path="/users/{id}",
            method=HTTPMethod.GET,
            operation_id="getUser",
            parameters=[
                ParameterDefinition("id", ParameterLocation.PATH, DataType.STRING, True),
                ParameterDefinition("fields", ParameterLocation.QUERY, DataType.STRING, False),
                ParameterDefinition("Authorization", ParameterLocation.HEADER, DataType.STRING, True),
            ]
        )
        
        assert len(endpoint.path_parameters) == 1
        assert len(endpoint.query_parameters) == 1
        assert len(endpoint.header_parameters) == 1
        assert len(endpoint.required_parameters) == 2


class TestOpenAPISpec:
    """Test OpenAPI spec dataclass."""
    
    def test_create_spec(self):
        spec = OpenAPISpec(
            title="Test API",
            version="1.0.0",
            description="Test",
            base_url="https://api.test.com",
            endpoints=[]
        )
        
        assert spec.title == "Test API"
        assert spec.endpoint_count == 0
    
    def test_methods_used(self):
        spec = OpenAPISpec(
            title="Test API",
            version="1.0.0",
            description="",
            base_url="",
            endpoints=[
                EndpointDefinition("/a", HTTPMethod.GET, "a"),
                EndpointDefinition("/b", HTTPMethod.POST, "b"),
                EndpointDefinition("/c", HTTPMethod.GET, "c"),
            ]
        )
        
        assert spec.methods_used == {HTTPMethod.GET, HTTPMethod.POST}


class TestAPIIngestionEngine:
    """Test the ingestion engine."""
    
    def setup_method(self):
        reset_ingestion_engine()
    
    def test_ingest_openapi_3(self):
        engine = APIIngestionEngine()
        spec = engine.ingest(SAMPLE_OPENAPI_3)
        
        assert spec.title == "Sample API"
        assert spec.version == "1.0.0"
        assert spec.openapi_version == "3.0.0"
        assert spec.endpoint_count == 3
    
    def test_ingest_swagger_2(self):
        engine = APIIngestionEngine()
        spec = engine.ingest(SAMPLE_SWAGGER_2)
        
        assert spec.title == "Legacy API"
        assert spec.version == "2.0.0"
        assert spec.openapi_version == "2.0"
        assert spec.endpoint_count == 1
    
    def test_ingest_invalid_spec(self):
        engine = APIIngestionEngine()
        
        with pytest.raises(IngestionError):
            engine.ingest({"invalid": "spec"})
    
    def test_ingest_json_string(self):
        engine = APIIngestionEngine()
        import json
        
        spec = engine.ingest_json(json.dumps(SAMPLE_OPENAPI_3))
        assert spec.title == "Sample API"
    
    def test_ingest_invalid_json(self):
        engine = APIIngestionEngine()
        
        with pytest.raises(IngestionError):
            engine.ingest_json("not valid json")
    
    def test_list_specs(self):
        engine = APIIngestionEngine()
        
        engine.ingest(SAMPLE_OPENAPI_3, "spec1")
        engine.ingest(SAMPLE_SWAGGER_2, "spec2")
        
        specs = engine.list_specs()
        assert "spec1" in specs
        assert "spec2" in specs
    
    def test_get_spec(self):
        engine = APIIngestionEngine()
        
        engine.ingest(SAMPLE_OPENAPI_3, "my-spec")
        
        spec = engine.get_spec("my-spec")
        assert spec is not None
        assert spec.title == "Sample API"
        
        assert engine.get_spec("nonexistent") is None


class TestEndpointParsing:
    """Test endpoint parsing details."""
    
    def test_parse_parameters(self):
        engine = APIIngestionEngine()
        spec = engine.ingest(SAMPLE_OPENAPI_3)
        
        # Find GET /users endpoint
        get_users = next(
            e for e in spec.endpoints
            if e.path == "/users" and e.method == HTTPMethod.GET
        )
        
        assert len(get_users.parameters) == 1
        assert get_users.parameters[0].name == "limit"
        assert get_users.parameters[0].location == ParameterLocation.QUERY
    
    def test_parse_request_body(self):
        engine = APIIngestionEngine()
        spec = engine.ingest(SAMPLE_OPENAPI_3)
        
        # Find POST /users endpoint
        post_users = next(
            e for e in spec.endpoints
            if e.path == "/users" and e.method == HTTPMethod.POST
        )
        
        assert post_users.request_body_schema is not None
        assert post_users.request_body_schema["type"] == "object"
    
    def test_parse_tags(self):
        engine = APIIngestionEngine()
        spec = engine.ingest(SAMPLE_OPENAPI_3)
        
        assert "users" in spec.tags_used
        
        user_endpoints = spec.get_endpoints_by_tag("users")
        assert len(user_endpoints) == 3


class TestGlobalFunctions:
    """Test module-level convenience functions."""
    
    def setup_method(self):
        reset_ingestion_engine()
    
    def test_get_singleton(self):
        e1 = get_ingestion_engine()
        e2 = get_ingestion_engine()
        assert e1 is e2
    
    def test_ingest_openapi_function(self):
        spec = ingest_openapi(SAMPLE_OPENAPI_3)
        assert spec.title == "Sample API"
    
    def test_reset_clears_state(self):
        engine = get_ingestion_engine()
        engine.ingest(SAMPLE_OPENAPI_3, "test")
        
        reset_ingestion_engine()
        
        new_engine = get_ingestion_engine()
        assert len(new_engine.list_specs()) == 0
