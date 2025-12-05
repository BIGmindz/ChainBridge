"""
Operator Console Backend Integration Guide

This document provides step-by-step instructions for integrating the new Operator Console
API endpoints into the existing ChainBridge FastAPI application.

Created: 2025-11-19
For: Cody (Backend/Integration Lead)
Status: Ready for Implementation
"""

# ===== QUICK START =====

"""
To integrate the Operator Console API endpoints:

1. Register router in api/server.py or api/main.py
2. Implement database query functions
3. Run tests to validate endpoints
4. Wire frontend to backend endpoints
5. Deploy and monitor

Total estimated time: 4-6 hours for full implementation
"""

# ===== STEP 1: Register Router in Main App =====

"""
File: api/server.py (or api/main.py, depending on your app structure)

BEFORE (example):
    from api.routes import chainboard, chainpay, settlements

    app = FastAPI(title="ChainBridge API")
    app.include_router(chainboard.router)
    app.include_router(chainpay.router)
    app.include_router(settlements.router)

AFTER (add operator router):
    from api.routes import chainboard, chainpay, settlements, chainiq_operator

    app = FastAPI(title="ChainBridge API")
    app.include_router(chainboard.router)
    app.include_router(chainpay.router)
    app.include_router(settlements.router)
    app.include_router(chainiq_operator.router)  # <-- NEW

This makes endpoints available at:
    - GET /chainiq/operator/summary
    - GET /chainiq/operator/queue
"""

# ===== STEP 2: Implement Database Query Functions =====

"""
File: api/routes/chainiq_operator.py (in the stub implementations)

Replace the stub implementations with actual database queries.

## 2.1 Implement get_operator_summary()

PSEUDOCODE:
    async def get_operator_summary() -> OperatorSummaryResponse:
        # Count total at-risk shipments
        total = db.query(AtRiskShipment).filter(AtRiskShipment.is_active==True).count()

        # Count by risk level
        critical = db.query(AtRiskShipment).filter(
            AtRiskShipment.is_active==True,
            AtRiskShipment.risk_level=='CRITICAL'
        ).count()

        high = db.query(AtRiskShipment).filter(
            AtRiskShipment.is_active==True,
            AtRiskShipment.risk_level=='HIGH'
        ).count()

        # Count shipments needing snapshots
        needs_snap = db.query(AtRiskShipment).filter(
            AtRiskShipment.is_active==True,
            (AtRiskShipment.latest_snapshot_status.is_(None) |
             AtRiskShipment.latest_snapshot_status != 'SUCCESS')
        ).count()

        # Return response
        return OperatorSummaryResponse(
            total_at_risk=total,
            critical_count=critical,
            high_count=high,
            needs_snapshot_count=needs_snap,
            payment_holds_count=0,  # Stub for now
            last_updated_at=datetime.now(timezone.utc),
        )

KEY NOTES:

- All counts should use is_active==True filter (exclude completed shipments)
- Use efficient COUNT(*) aggregate queries, not row-by-row iteration
- Shipment "needs snapshot" = (latest_snapshot_status IS NULL OR != 'SUCCESS')
  This includes: None, FAILED, IN_PROGRESS, PENDING
- payment_holds_count is stub (0) until ChainPay integration wired


## 2.2 Implement get_operator_queue()

PSEUDOCODE:
    async def get_operator_queue(
        max_results: int = 50,
        include_levels: str = "CRITICAL,HIGH",
        needs_snapshot_only: bool = False,
    ) -> List[OperatorQueueItem]:

        # Parse include_levels parameter
        levels = [l.strip() for l in include_levels.split(",")]

        # Build base query
        query = db.query(AtRiskShipment).filter(AtRiskShipment.is_active==True)

        # Filter by risk levels
        query = query.filter(AtRiskShipment.risk_level.in_(levels))

        # Filter by snapshot need if requested
        if needs_snapshot_only:
            query = query.filter(
                (AtRiskShipment.latest_snapshot_status.is_(None) |
                 AtRiskShipment.latest_snapshot_status != 'SUCCESS')
            )

        # Apply sorting rules (in order):
        # 1. Needs snapshot DESC (True first)
        # 2. Risk level (CRITICAL=4, HIGH=3, MODERATE=2, LOW=1)
        # 3. Risk score DESC
        # 4. Days delayed DESC
        # 5. Shipment ID ASC (stability)

        from sqlalchemy import case, desc

        query = query.order_by(
            # Rule 1: Needs snapshot first
            desc(case(
                (AtRiskShipment.latest_snapshot_status.is_(None), 1),
                (AtRiskShipment.latest_snapshot_status != 'SUCCESS', 1),
                else_=0
            )),
            # Rule 2: Risk level priority
            desc(case(
                (AtRiskShipment.risk_level=='CRITICAL', 4),
                (AtRiskShipment.risk_level=='HIGH', 3),
                (AtRiskShipment.risk_level=='MODERATE', 2),
                (AtRiskShipment.risk_level=='LOW', 1),
                else_=0
            )),
            # Rule 3: Risk score DESC
            desc(AtRiskShipment.risk_score),
            # Rule 4: Days delayed DESC
            desc(AtRiskShipment.days_delayed.or_(0)),
            # Rule 5: Shipment ID ASC (stable)
            AtRiskShipment.shipment_id.asc(),
        ).limit(max_results)

        # Fetch results
        shipments = query.all()

        # Convert to OperatorQueueItem objects
        items = []
        for shipment in shipments:
            item = OperatorQueueItem(
                shipment_id=shipment.shipment_id,
                risk_level=shipment.risk_level,
                risk_score=shipment.risk_score,
                corridor_code=shipment.corridor_code,
                mode=shipment.mode,
                incoterm=shipment.incoterm,
                completeness_pct=shipment.completeness_pct,
                blocking_gap_count=shipment.blocking_gap_count,
                template_name=shipment.template_name,
                days_delayed=shipment.days_delayed,
                latest_snapshot_status=shipment.latest_snapshot_status,
                latest_snapshot_updated_at=shipment.latest_snapshot_updated_at,
                needs_snapshot=(
                    shipment.latest_snapshot_status is None or
                    shipment.latest_snapshot_status != 'SUCCESS'
                ),
                has_payment_hold=False,  # Stub for now
                last_event_at=shipment.latest_snapshot_updated_at,
            )
            items.append(item)

        return items

KEY NOTES:

- CRITICAL PERFORMANCE: Use single database query with joins, NO N+1 loops
- The sorting must happen at the database level (ORDER BY clause) for performance
- include_levels default: "CRITICAL,HIGH" – only these by default
- needs_snapshot_only: If True, FURTHER filter to only snapshot-needing items
  (Does NOT just re-sort; actually filters results)
- has_payment_hold is always False (stub) until ChainPay integration
- last_event_at = latest_snapshot_updated_at (for potential timeline sorting)
"""

# ===== STEP 3: Wire Database Session Injection =====

"""
If your app uses dependency injection for database sessions:

FILE: api/routes/chainiq_operator.py

ADD dependency at top of file:
    from fastapi import APIRouter, Query, Depends
    from sqlalchemy.orm import Session
    from api.database import get_db  # Your DB session factory

MODIFY endpoints to accept db parameter:
    @router.get("/summary", response_model=OperatorSummaryResponse)
    async def get_operator_summary(db: Session = Depends(get_db)) -> OperatorSummaryResponse:
        # Implementation using db session
        pass

    @router.get("/queue", response_model=List[OperatorQueueItem])
    async def get_operator_queue(
        max_results: int = Query(50, ge=1, le=500),
        include_levels: Optional[str] = Query("CRITICAL,HIGH"),
        needs_snapshot_only: bool = Query(False),
        db: Session = Depends(get_db),  # <-- ADD THIS
    ) -> List[OperatorQueueItem]:
        # Implementation using db session
        pass
"""

# ===== STEP 4: Validate Database Models =====

"""
Ensure your AtRiskShipment model has these fields (used by queries):

FROM api/models/chainiq.py (or similar):

    class AtRiskShipment(Base):
        __tablename__ = "at_risk_shipments"

        # Core fields
        shipment_id: str = Column(String, primary_key=True)
        risk_level: str = Column(String)  # CRITICAL, HIGH, MODERATE, LOW
        risk_score: float = Column(Float)
        is_active: bool = Column(Boolean, default=True)

        # Document/template fields
        corridor_code: str = Column(String, nullable=True)
        mode: str = Column(String, nullable=True)  # OCEAN, AIR, ROAD, RAIL
        incoterm: str = Column(String, nullable=True)
        completeness_pct: int = Column(Integer)
        blocking_gap_count: int = Column(Integer)
        template_name: str = Column(String, nullable=True)

        # Timeline fields
        days_delayed: int = Column(Integer, nullable=True)
        latest_snapshot_status: str = Column(String, nullable=True)  # SUCCESS, FAILED, etc.
        latest_snapshot_updated_at: datetime = Column(DateTime, nullable=True)

        # Timestamps
        created_at: datetime = Column(DateTime)
        updated_at: datetime = Column(DateTime)

If fields are missing, add them or adjust query to use available fields.
"""

# ===== STEP 5: Test Implementation =====

"""
Run tests to validate endpoints:

    cd /Users/johnbozza/Documents/Projects/ChainBridge-local-repo/ChainBridge

    # Run all operator tests
    pytest tests/test_chainiq_operator.py -v

    # Run specific test class
    pytest tests/test_chainiq_operator.py::TestOperatorSummary -v

    # Run with database fixture (if using)
    pytest tests/test_chainiq_operator.py -v --fixtures

    # Run with coverage
    pytest tests/test_chainiq_operator.py --cov=api.routes.chainiq_operator --cov-report=html

Expected test status BEFORE implementation:
    - All tests will have pytest.skip() with "TODO: Implement with database setup"
    - Tests document expected behavior and validation rules
    - Once database queries are implemented, remove pytest.skip() to enable tests

Example test run (once implemented):
    tests/test_chainiq_operator.py::TestOperatorSummary::test_summary_returns_correct_schema PASSED
    tests/test_chainiq_operator.py::TestOperatorSummary::test_summary_counts_are_accurate PASSED
    tests/test_chainiq_operator.py::TestOperatorQueue::test_queue_sorting_rule_1_snapshot_need_first PASSED
    tests/test_chainiq_operator.py::TestOperatorQueue::test_queue_sorting_rule_2_risk_level_priority PASSED
    ...
"""

# ===== STEP 6: Manual Testing with curl =====

"""
Test endpoints manually before integrating with frontend:

    # Test 1: Get summary
    curl -s http://localhost:8001/chainiq/operator/summary | jq .

    Expected response:
    {
      "total_at_risk": 42,
      "critical_count": 3,
      "high_count": 8,
      "needs_snapshot_count": 5,
      "payment_holds_count": 0,
      "last_updated_at": "2025-11-19T12:00:00Z"
    }

    # Test 2: Get queue (default)
    curl -s http://localhost:8001/chainiq/operator/queue | jq .

    # Test 3: Get CRITICAL only
    curl -s "http://localhost:8001/chainiq/operator/queue?include_levels=CRITICAL" | jq .

    # Test 4: Get items needing snapshots
    curl -s "http://localhost:8001/chainiq/operator/queue?needs_snapshot_only=true" | jq .

    # Test 5: Get top 10 CRITICAL/HIGH needing snapshots
    curl -s "http://localhost:8001/chainiq/operator/queue?include_levels=CRITICAL,HIGH&needs_snapshot_only=true&max_results=10" | jq .

    # View full response with headers
    curl -i http://localhost:8001/chainiq/operator/summary
"""

# ===== STEP 7: Wire Frontend to Backend =====

"""
File: chainboard-ui/src/pages/OperatorConsolePage.tsx

Replace frontend-derived queue with backend-driven queue:

BEFORE (frontend sorting):
    const { data: shipments } = useAtRiskShipments({...});
    const priorityQueue = React.useMemo(() => prioritizeQueue(shipments), [shipments]);

AFTER (backend sorting):
    // For summary
    const { data: summary, isLoading: summaryLoading } = useQuery({
      queryKey: ["operatorSummary"],
      queryFn: async () => {
        const response = await apiClient.httpGet("/chainiq/operator/summary");
        return response as OperatorSummaryResponse;
      },
      refetchInterval: 15_000,  // Poll every 15s
    });

    // For queue (with filters from search params)
    const { data: priorityQueue, isLoading: queueLoading } = useQuery({
      queryKey: ["operatorQueue", filters],
      queryFn: async () => {
        const params = new URLSearchParams({
          max_results: "50",
          include_levels: filters.include_levels || "CRITICAL,HIGH",
          needs_snapshot_only: filters.needs_snapshot_only ? "true" : "false",
        });
        const response = await apiClient.httpGet(
          `/chainiq/operator/queue?${params.toString()}`
        );
        return response as OperatorQueueItem[];
      },
      refetchInterval: 5_000,  // Poll every 5s
    });

Benefits:
    - Server-side sorting ensures consistency across users
    - Reduced frontend logic complexity
    - Better performance with database indexes
    - Easier to add new sorting rules on backend
    - Payment holds/ChainPay integration only needs backend update
"""

# ===== STEP 8: Add Authorization Checks =====

"""
Once auth system is implemented, add authorization to endpoints:

FILE: api/routes/chainiq_operator.py

    from api.auth import get_current_user, require_role

    @router.get("/summary", response_model=OperatorSummaryResponse)
    async def get_operator_summary(
        db: Session = Depends(get_db),
        current_user = Depends(get_current_user),
    ) -> OperatorSummaryResponse:
        # Verify user has OPERATOR or ADMIN role
        if current_user.role not in ["OPERATOR", "ADMIN"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        # Implementation...
        pass

Add to endpoints:
    - current_user = Depends(get_current_user)
    - current_tenant_id = current_user.tenant_id (for multi-tenant filtering)
    - Role checks: require OPERATOR, SUPERVISOR, or ADMIN role
"""

# ===== STEP 9: Monitor & Debug =====

"""
Add logging and monitoring:

FILE: api/routes/chainiq_operator.py

    import logging
    logger = logging.getLogger(__name__)

    @router.get("/summary", response_model=OperatorSummaryResponse)
    async def get_operator_summary(db: Session = Depends(get_db)) -> OperatorSummaryResponse:
        logger.info("Fetching operator summary")

        try:
            # Query implementation
            result = ...
            logger.info(f"Operator summary: {result.total_at_risk} at-risk shipments")
            return result
        except Exception as e:
            logger.error(f"Error fetching operator summary: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")

Monitor:
    - Query performance (target <500ms for both endpoints)
    - Error rates (target <1%)
    - P99 latency (target <1000ms even at peak)
"""

# ===== STEP 10: Production Deployment =====

"""
Before deploying to production:

1. Run full test suite
   pytest tests/test_chainiq_operator.py -v --cov

2. Performance test with realistic data volume
   Load test with 10k+ at-risk shipments
   Verify both endpoints respond <500ms at p99

3. Database indexing
   Ensure indexes on:
   - at_risk_shipments(is_active, risk_level)
   - at_risk_shipments(is_active, latest_snapshot_status)
   - at_risk_shipments(is_active, risk_score)

4. Cache layer (optional, if needed)
   Consider Redis caching for summary (ttl=5s)
   Queue is already efficient, probably doesn't need cache

5. Monitor in production
   Set up alerts for:
   - Endpoint response time > 1000ms
   - Error rate > 1%
   - Database query slow log > 500ms

6. Documentation
   Update API docs (if using OpenAPI/Swagger)
   Endpoints auto-generate from docstrings
"""

# ===== IMPLEMENTATION CHECKLIST =====

"""
✅ COMPLETED (by Sonny/Frontend Team):
  [x] Created OperatorConsolePage.tsx (2-column layout, action-first UI)
  [x] Component structure with priority queue visualization
  [x] Export snapshot button with React Query integration
  [x] Timeline display with auto-polling
  [x] Comprehensive documentation

✅ CREATED (by Cody/Backend Team, this file):
  [x] chainiq_operator.py with endpoint stubs
  [x] Pydantic schemas (OperatorSummaryResponse, OperatorQueueItem)
  [x] Comprehensive test suite (test_chainiq_operator.py)
  [x] This integration guide

📋 TODO (Cody/Backend Team, next steps):
  [ ] Register router in api/server.py
  [ ] Implement get_operator_summary() with database query
  [ ] Implement get_operator_queue() with database query & sorting
  [ ] Wire database session injection (Depends(get_db))
  [ ] Validate database models have required fields
  [ ] Run tests: pytest tests/test_chainiq_operator.py -v
  [ ] Manual testing with curl
  [ ] Verify query performance (<500ms both endpoints)
  [ ] Add database indexes
  [ ] Wire frontend: OperatorConsolePage.tsx → backend endpoints
  [ ] Add authorization checks (once auth system ready)
  [ ] Add logging and monitoring
  [ ] Performance test with realistic data
  [ ] Deploy to production

📋 TODO (Sonny/Frontend Team, after backend):
  [ ] Switch OperatorConsolePage from frontend sorting to backend endpoint
  [ ] Add useQuery for operator summary (/chainiq/operator/summary)
  [ ] Add useQuery for operator queue (/chainiq/operator/queue)
  [ ] Wire filter controls to query params
  [ ] Test full round-trip flow
  [ ] Deploy to production

Total work remaining: ~6-8 hours (backend implementation + testing)
"""
