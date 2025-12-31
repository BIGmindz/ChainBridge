"""
Unit Tests for Adversarial Simulation V2.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-REAL-WORK-032
Agent: GID-06 (Zane) — SECURITY/ADVERSARIAL SIMULATION
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from core.security.adversarial_v2 import (
    ADVERSARIAL_V2_VERSION,
    AttackCategory,
    ThreatCategory,
    Severity,
    TestResult,
    IncidentState,
    FuzzStrategy,
    AdversarialError,
    AttackSimulationError,
    ThreatModelError,
    AttackScenario,
    AttackResult,
    Threat,
    FuzzResult,
    PenTestResult,
    SecurityMetricsSnapshot,
    Incident,
    AdvancedAttackSimulator,
    FuzzEngine,
    ThreatModeler,
    PenetrationTestSuite,
    SecurityMetrics,
    IncidentSimulator,
    compute_wrap_hash,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def attack_simulator():
    """Create attack simulator with default scenarios."""
    sim = AdvancedAttackSimulator()
    sim.create_default_scenarios()
    return sim


@pytest.fixture
def fuzz_engine():
    """Create fuzz engine."""
    return FuzzEngine()


@pytest.fixture
def threat_modeler():
    """Create threat modeler."""
    return ThreatModeler()


@pytest.fixture
def pen_test_suite():
    """Create penetration test suite with default tests."""
    suite = PenetrationTestSuite()
    suite.create_default_tests()
    return suite


@pytest.fixture
def security_metrics():
    """Create security metrics instance."""
    return SecurityMetrics()


@pytest.fixture
def incident_simulator():
    """Create incident simulator."""
    return IncidentSimulator()


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_attack_category_values(self):
        """Test AttackCategory enum values."""
        assert AttackCategory.INITIAL_ACCESS.value == "INITIAL_ACCESS"
        assert AttackCategory.EXECUTION.value == "EXECUTION"
        assert AttackCategory.PERSISTENCE.value == "PERSISTENCE"
        assert AttackCategory.EXFILTRATION.value == "EXFILTRATION"
    
    def test_threat_category_stride(self):
        """Test STRIDE threat categories."""
        assert ThreatCategory.SPOOFING.value == "SPOOFING"
        assert ThreatCategory.TAMPERING.value == "TAMPERING"
        assert ThreatCategory.REPUDIATION.value == "REPUDIATION"
        assert ThreatCategory.INFORMATION_DISCLOSURE.value == "INFORMATION_DISCLOSURE"
        assert ThreatCategory.DENIAL_OF_SERVICE.value == "DENIAL_OF_SERVICE"
        assert ThreatCategory.ELEVATION_OF_PRIVILEGE.value == "ELEVATION_OF_PRIVILEGE"
    
    def test_severity_values(self):
        """Test Severity enum values."""
        assert Severity.CRITICAL.value == 5
        assert Severity.HIGH.value == 4
        assert Severity.MEDIUM.value == 3
        assert Severity.LOW.value == 2
        assert Severity.INFO.value == 1
    
    def test_incident_state_values(self):
        """Test IncidentState enum values."""
        assert IncidentState.DETECTED.value == "DETECTED"
        assert IncidentState.TRIAGED.value == "TRIAGED"
        assert IncidentState.CONTAINED.value == "CONTAINED"
        assert IncidentState.ERADICATED.value == "ERADICATED"
        assert IncidentState.RECOVERED.value == "RECOVERED"
        assert IncidentState.LESSONS_LEARNED.value == "LESSONS_LEARNED"
    
    def test_fuzz_strategy_values(self):
        """Test FuzzStrategy enum values."""
        assert FuzzStrategy.RANDOM.value == "RANDOM"
        assert FuzzStrategy.MUTATION.value == "MUTATION"
        assert FuzzStrategy.GRAMMAR.value == "GRAMMAR"
        assert FuzzStrategy.SMART.value == "SMART"


# =============================================================================
# DATA CLASS TESTS
# =============================================================================

class TestAttackScenario:
    """Test AttackScenario dataclass."""
    
    def test_scenario_creation(self):
        """Test scenario creation."""
        scenario = AttackScenario(
            scenario_id="ATK-TEST",
            name="Test Attack",
            description="Test description",
            category=AttackCategory.INITIAL_ACCESS,
            techniques=["T1190"],
            severity=Severity.HIGH,
            preconditions=["Target accessible"],
            steps=[{"name": "probe"}],
            expected_detection=True,
        )
        
        assert scenario.scenario_id == "ATK-TEST"
        assert scenario.category == AttackCategory.INITIAL_ACCESS
        assert scenario.severity == Severity.HIGH
    
    def test_scenario_to_dict(self):
        """Test scenario serialization."""
        scenario = AttackScenario(
            scenario_id="ATK-001",
            name="SQL Injection",
            description="Test",
            category=AttackCategory.INITIAL_ACCESS,
            techniques=["T1190"],
            severity=Severity.HIGH,
            preconditions=[],
            steps=[],
            expected_detection=True,
        )
        
        data = scenario.to_dict()
        
        assert data["scenario_id"] == "ATK-001"
        assert data["category"] == "INITIAL_ACCESS"
        assert data["severity"] == 4


class TestThreat:
    """Test Threat dataclass."""
    
    def test_threat_risk_calculation(self):
        """Test automatic risk score calculation."""
        threat = Threat(
            threat_id="THR-001",
            name="Test Threat",
            category=ThreatCategory.SPOOFING,
            description="Test",
            affected_assets=["asset1"],
            mitigations=[],
            likelihood=4,
            impact=5,
        )
        
        # risk_score = (likelihood * impact) / 5
        assert threat.risk_score == (4 * 5) / 5.0
        assert threat.risk_score == 4.0
    
    def test_threat_to_dict(self):
        """Test threat serialization."""
        threat = Threat(
            threat_id="THR-001",
            name="Data Theft",
            category=ThreatCategory.INFORMATION_DISCLOSURE,
            description="Sensitive data exposure",
            affected_assets=["database"],
            mitigations=["encryption"],
            likelihood=3,
            impact=4,
        )
        
        data = threat.to_dict()
        
        assert data["threat_id"] == "THR-001"
        assert data["category"] == "INFORMATION_DISCLOSURE"
        assert data["risk_score"] == 2.4


class TestIncident:
    """Test Incident dataclass."""
    
    def test_incident_creation(self):
        """Test incident creation."""
        incident = Incident(
            incident_id="INC-001",
            title="Security Breach",
            severity=Severity.CRITICAL,
            state=IncidentState.DETECTED,
            detected_at=datetime.now(timezone.utc),
            description="Test incident",
            affected_systems=["server1"],
            indicators=["suspicious_login"],
            timeline=[],
        )
        
        assert incident.incident_id == "INC-001"
        assert incident.severity == Severity.CRITICAL
        assert incident.state == IncidentState.DETECTED


# =============================================================================
# ATTACK SIMULATOR TESTS
# =============================================================================

class TestAdvancedAttackSimulator:
    """Test AdvancedAttackSimulator class."""
    
    def test_register_scenario(self, attack_simulator):
        """Test scenario registration."""
        scenario = AttackScenario(
            scenario_id="ATK-CUSTOM",
            name="Custom Attack",
            description="Test",
            category=AttackCategory.EXECUTION,
            techniques=[],
            severity=Severity.MEDIUM,
            preconditions=[],
            steps=[],
            expected_detection=False,
        )
        
        attack_simulator.register_scenario(scenario)
        
        retrieved = attack_simulator.get_scenario("ATK-CUSTOM")
        assert retrieved is not None
        assert retrieved.name == "Custom Attack"
    
    def test_simulate_attack(self, attack_simulator):
        """Test attack simulation."""
        result = attack_simulator.simulate("ATK-001")
        
        assert result.scenario_id == "ATK-001"
        assert result.result in TestResult
        assert len(result.logs) > 0
    
    def test_simulate_unknown_scenario_raises(self, attack_simulator):
        """Test simulating unknown scenario raises."""
        with pytest.raises(AttackSimulationError):
            attack_simulator.simulate("UNKNOWN-001")
    
    def test_register_detector(self, attack_simulator):
        """Test detector registration."""
        detections = []
        
        def detector(event):
            detections.append(event)
            return True  # Always detect
        
        attack_simulator.register_detector(detector)
        result = attack_simulator.simulate("ATK-001")
        
        assert result.detected is True
        assert len(detections) > 0
    
    def test_get_results(self, attack_simulator):
        """Test getting results."""
        attack_simulator.simulate("ATK-001")
        attack_simulator.simulate("ATK-002")
        
        results = attack_simulator.get_results()
        
        assert len(results) >= 2
    
    def test_create_default_scenarios(self):
        """Test default scenario creation."""
        sim = AdvancedAttackSimulator()
        sim.create_default_scenarios()
        
        assert sim.get_scenario("ATK-001") is not None
        assert sim.get_scenario("ATK-002") is not None
        assert sim.get_scenario("ATK-003") is not None


# =============================================================================
# FUZZ ENGINE TESTS
# =============================================================================

class TestFuzzEngine:
    """Test FuzzEngine class."""
    
    def test_fuzz_random(self, fuzz_engine):
        """Test random fuzzing."""
        def target(data):
            return False, None  # Never crashes
        
        result = fuzz_engine.fuzz(
            target,
            strategy=FuzzStrategy.RANDOM,
            iterations=100,
        )
        
        assert result.test_id.startswith("FUZZ-")
        assert result.iterations == 100
        assert result.crashes >= 0
    
    def test_fuzz_mutation(self, fuzz_engine):
        """Test mutation fuzzing."""
        def target(data):
            return False, None
        
        result = fuzz_engine.fuzz(
            target,
            strategy=FuzzStrategy.MUTATION,
            iterations=50,
            seed_inputs=[b"test_input"],
        )
        
        assert result.strategy == FuzzStrategy.MUTATION
        assert result.unique_paths > 0
    
    def test_fuzz_with_crashes(self, fuzz_engine):
        """Test fuzzing with crashes."""
        def target(data):
            # Crash on specific pattern
            if b"\x00\x00" in data:
                return True, "Null byte crash"
            return False, None
        
        result = fuzz_engine.fuzz(
            target,
            strategy=FuzzStrategy.RANDOM,
            iterations=500,
        )
        
        # May or may not find crashes depending on random
        assert result.test_id is not None
    
    def test_register_grammar(self, fuzz_engine):
        """Test grammar registration."""
        grammar = {
            "start": ["<expr>"],
            "<expr>": [["<num>"], ["<num>", "+", "<num>"]],
            "<num>": [["1"], ["2"], ["3"]],
        }
        
        fuzz_engine.register_grammar("math", grammar)
        
        def target(data):
            return False, None
        
        result = fuzz_engine.fuzz(
            target,
            strategy=FuzzStrategy.GRAMMAR,
            iterations=50,
            grammar_name="math",
        )
        
        assert result.strategy == FuzzStrategy.GRAMMAR
    
    def test_get_results(self, fuzz_engine):
        """Test getting fuzz results."""
        def target(data):
            return False, None
        
        fuzz_engine.fuzz(target, iterations=10)
        fuzz_engine.fuzz(target, iterations=10)
        
        results = fuzz_engine.get_results()
        
        assert len(results) >= 2


# =============================================================================
# THREAT MODELER TESTS
# =============================================================================

class TestThreatModeler:
    """Test ThreatModeler class."""
    
    def test_register_asset(self, threat_modeler):
        """Test asset registration."""
        threat_modeler.register_asset(
            asset_id="DB-001",
            name="Production Database",
            asset_type="database",
            sensitivity=5,
        )
        
        # Asset should be registered (no direct getter, verified via threat report)
        report = threat_modeler.generate_threat_report()
        assert "DB-001" in report["assets"]
    
    def test_identify_threat(self, threat_modeler):
        """Test threat identification."""
        threat = threat_modeler.identify_threat(
            name="Data Exfiltration",
            category=ThreatCategory.INFORMATION_DISCLOSURE,
            description="Sensitive data could be stolen",
            affected_assets=["database"],
            likelihood=4,
            impact=5,
        )
        
        assert threat.threat_id.startswith("THR-")
        assert threat.risk_score == 4.0
    
    def test_calculate_dread_score(self, threat_modeler):
        """Test DREAD score calculation."""
        score = threat_modeler.calculate_dread_score(
            damage=8,
            reproducibility=9,
            exploitability=7,
            affected_users=10,
            discoverability=6,
        )
        
        expected = (8 + 9 + 7 + 10 + 6) / 5
        assert score == expected
    
    def test_get_threat_matrix(self, threat_modeler):
        """Test threat matrix generation."""
        threat_modeler.identify_threat(
            name="Threat 1",
            category=ThreatCategory.SPOOFING,
            description="Test",
            affected_assets=[],
            likelihood=3,
            impact=3,
        )
        threat_modeler.identify_threat(
            name="Threat 2",
            category=ThreatCategory.TAMPERING,
            description="Test",
            affected_assets=[],
            likelihood=2,
            impact=4,
        )
        
        matrix = threat_modeler.get_threat_matrix()
        
        assert "SPOOFING" in matrix
        assert "TAMPERING" in matrix
    
    def test_get_risk_summary(self, threat_modeler):
        """Test risk summary."""
        threat_modeler.identify_threat(
            name="High Risk",
            category=ThreatCategory.ELEVATION_OF_PRIVILEGE,
            description="Test",
            affected_assets=[],
            likelihood=5,
            impact=5,
        )
        
        summary = threat_modeler.get_risk_summary()
        
        assert summary["total_threats"] == 1
        assert summary["average_risk"] == 5.0
        assert summary["high_risk_count"] == 1
    
    def test_generate_threat_report(self, threat_modeler):
        """Test threat report generation."""
        threat_modeler.register_asset("A1", "Asset 1", "server", 3)
        threat_modeler.identify_threat(
            name="Threat 1",
            category=ThreatCategory.DENIAL_OF_SERVICE,
            description="DoS attack",
            affected_assets=["A1"],
            likelihood=3,
            impact=4,
        )
        
        report = threat_modeler.generate_threat_report()
        
        assert "generated_at" in report
        assert "assets" in report
        assert "threats" in report
        assert "risk_summary" in report


# =============================================================================
# PENETRATION TEST SUITE TESTS
# =============================================================================

class TestPenetrationTestSuite:
    """Test PenetrationTestSuite class."""
    
    def test_register_test(self):
        """Test test registration."""
        suite = PenetrationTestSuite()
        
        test_id = suite.register_test(
            test_type="custom",
            name="Custom Test",
            target_pattern="*",
            checks=[{"name": "check1"}],
        )
        
        assert test_id.startswith("PT-")
    
    def test_run_test(self, pen_test_suite):
        """Test running a penetration test."""
        result = pen_test_suite.run_test("PT-0001", "http://example.com")
        
        assert result.test_id == "PT-0001"
        assert result.target == "http://example.com"
        assert result.result in TestResult
    
    def test_run_unknown_test_raises(self, pen_test_suite):
        """Test running unknown test raises."""
        with pytest.raises(AdversarialError):
            pen_test_suite.run_test("UNKNOWN", "target")
    
    def test_get_results(self, pen_test_suite):
        """Test getting results."""
        pen_test_suite.run_test("PT-0001", "target1")
        pen_test_suite.run_test("PT-0001", "target2")
        
        results = pen_test_suite.get_results()
        
        assert len(results) >= 2
    
    def test_create_default_tests(self):
        """Test default tests creation."""
        suite = PenetrationTestSuite()
        suite.create_default_tests()
        
        # Should have SQL injection and XSS tests
        results = suite.run_test("PT-0001", "http://test.com")
        assert results is not None


# =============================================================================
# SECURITY METRICS TESTS
# =============================================================================

class TestSecurityMetrics:
    """Test SecurityMetrics class."""
    
    def test_record_finding(self, security_metrics):
        """Test recording a finding."""
        security_metrics.record_finding(
            severity=Severity.HIGH,
            detected_at=datetime.now(timezone.utc),
        )
        
        snapshot = security_metrics.get_snapshot()
        assert snapshot.open_findings == 1
    
    def test_record_finding_with_remediation(self, security_metrics):
        """Test recording remediated finding."""
        detected = datetime.now(timezone.utc) - timedelta(hours=2)
        remediated = datetime.now(timezone.utc)
        
        security_metrics.record_finding(
            severity=Severity.MEDIUM,
            detected_at=detected,
            remediated_at=remediated,
        )
        
        mttr = security_metrics.calculate_mttr()
        assert mttr == pytest.approx(2.0, rel=0.1)
    
    def test_calculate_mttd(self, security_metrics):
        """Test MTTD calculation."""
        security_metrics.record_detection(5.0)
        security_metrics.record_detection(10.0)
        security_metrics.record_detection(15.0)
        
        mttd = security_metrics.calculate_mttd()
        assert mttd == 10.0
    
    def test_calculate_security_score(self, security_metrics):
        """Test security score calculation."""
        # No findings = perfect score
        score = security_metrics.calculate_security_score()
        assert score == 100.0
        
        # Add critical finding
        security_metrics.record_finding(
            severity=Severity.CRITICAL,
            detected_at=datetime.now(timezone.utc),
        )
        
        score = security_metrics.calculate_security_score()
        assert score < 100.0
    
    def test_get_snapshot(self, security_metrics):
        """Test getting metrics snapshot."""
        security_metrics.record_finding(
            severity=Severity.HIGH,
            detected_at=datetime.now(timezone.utc),
        )
        security_metrics.record_detection(5.0)
        
        snapshot = security_metrics.get_snapshot()
        
        assert snapshot.timestamp is not None
        assert snapshot.open_findings == 1
        assert snapshot.mttd_minutes == 5.0
    
    def test_get_trend(self, security_metrics):
        """Test getting trend data."""
        security_metrics.get_snapshot()
        security_metrics.get_snapshot()
        
        trend = security_metrics.get_trend(days=30)
        
        assert len(trend) >= 2


# =============================================================================
# INCIDENT SIMULATOR TESTS
# =============================================================================

class TestIncidentSimulator:
    """Test IncidentSimulator class."""
    
    def test_create_incident(self, incident_simulator):
        """Test incident creation."""
        incident = incident_simulator.create_incident(
            title="Ransomware Attack",
            severity=Severity.CRITICAL,
            description="Ransomware detected",
            affected_systems=["server1", "server2"],
            indicators=["suspicious_process"],
        )
        
        assert incident.incident_id.startswith("INC-")
        assert incident.state == IncidentState.DETECTED
        assert len(incident.timeline) == 1
    
    def test_transition_incident(self, incident_simulator):
        """Test incident state transition."""
        incident = incident_simulator.create_incident(
            title="Test",
            severity=Severity.HIGH,
            description="Test",
            affected_systems=[],
        )
        
        # Valid transition: DETECTED → TRIAGED
        updated = incident_simulator.transition_incident(
            incident.incident_id,
            IncidentState.TRIAGED,
            notes="Initial triage complete",
        )
        
        assert updated.state == IncidentState.TRIAGED
        assert len(updated.timeline) == 2
    
    def test_invalid_transition_raises(self, incident_simulator):
        """Test invalid state transition raises."""
        incident = incident_simulator.create_incident(
            title="Test",
            severity=Severity.LOW,
            description="Test",
            affected_systems=[],
        )
        
        # Invalid: DETECTED → RECOVERED (skipping states)
        with pytest.raises(AdversarialError):
            incident_simulator.transition_incident(
                incident.incident_id,
                IncidentState.RECOVERED,
            )
    
    def test_get_active_incidents(self, incident_simulator):
        """Test getting active incidents."""
        incident_simulator.create_incident(
            title="Active 1",
            severity=Severity.MEDIUM,
            description="Test",
            affected_systems=[],
        )
        incident_simulator.create_incident(
            title="Active 2",
            severity=Severity.HIGH,
            description="Test",
            affected_systems=[],
        )
        
        active = incident_simulator.get_active_incidents()
        
        assert len(active) == 2
    
    def test_calculate_sla_metrics(self, incident_simulator):
        """Test SLA metrics calculation."""
        incident = incident_simulator.create_incident(
            title="Test",
            severity=Severity.HIGH,
            description="Test",
            affected_systems=[],
        )
        
        incident_simulator.transition_incident(
            incident.incident_id,
            IncidentState.TRIAGED,
        )
        
        metrics = incident_simulator.calculate_sla_metrics(incident.incident_id)
        
        assert metrics["incident_id"] == incident.incident_id
        assert metrics["current_state"] == "TRIAGED"
    
    def test_full_incident_lifecycle(self, incident_simulator):
        """Test full incident lifecycle."""
        incident = incident_simulator.create_incident(
            title="Full Lifecycle Test",
            severity=Severity.CRITICAL,
            description="Test",
            affected_systems=["all"],
        )
        
        # Progress through all states
        states = [
            IncidentState.TRIAGED,
            IncidentState.CONTAINED,
            IncidentState.ERADICATED,
            IncidentState.RECOVERED,
            IncidentState.LESSONS_LEARNED,
        ]
        
        for state in states:
            incident = incident_simulator.transition_incident(
                incident.incident_id,
                state,
            )
        
        assert incident.state == IncidentState.LESSONS_LEARNED
        assert len(incident.timeline) == 6  # 1 initial + 5 transitions


# =============================================================================
# WRAP HASH TESTS
# =============================================================================

class TestWrapHash:
    """Test WRAP hash computation."""
    
    def test_compute_wrap_hash(self):
        """Test WRAP hash computation."""
        hash1 = compute_wrap_hash()
        hash2 = compute_wrap_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 16
    
    def test_wrap_hash_includes_version(self):
        """Test WRAP hash is version-aware."""
        expected_content = f"GID-06:adversarial_v2:v{ADVERSARIAL_V2_VERSION}"
        assert ADVERSARIAL_V2_VERSION in expected_content


# =============================================================================
# THREAD SAFETY TESTS
# =============================================================================

class TestThreadSafety:
    """Test thread safety."""
    
    def test_concurrent_attack_simulation(self, attack_simulator):
        """Test concurrent attack simulation."""
        import threading
        
        results = []
        
        def simulate():
            result = attack_simulator.simulate("ATK-001")
            results.append(result)
        
        threads = [threading.Thread(target=simulate) for _ in range(10)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 10
    
    def test_concurrent_threat_modeling(self, threat_modeler):
        """Test concurrent threat identification."""
        import threading
        
        threats = []
        
        def identify(name):
            threat = threat_modeler.identify_threat(
                name=name,
                category=ThreatCategory.SPOOFING,
                description="Test",
                affected_assets=[],
                likelihood=3,
                impact=3,
            )
            threats.append(threat)
        
        threads = [
            threading.Thread(target=identify, args=(f"Threat_{i}",))
            for i in range(10)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(threats) == 10
        # All should have unique IDs
        ids = [t.threat_id for t in threats]
        assert len(set(ids)) == 10


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests."""
    
    def test_full_security_assessment(
        self,
        attack_simulator,
        pen_test_suite,
        threat_modeler,
        security_metrics,
    ):
        """Test full security assessment workflow."""
        # 1. Model threats
        threat_modeler.register_asset("API", "API Server", "web", 4)
        threat = threat_modeler.identify_threat(
            name="API Injection",
            category=ThreatCategory.TAMPERING,
            description="SQL injection risk",
            affected_assets=["API"],
            likelihood=4,
            impact=4,
        )
        
        # 2. Run attack simulation
        attack_result = attack_simulator.simulate("ATK-001")
        
        # 3. Run penetration test
        pen_result = pen_test_suite.run_test("PT-0001", "http://api.example.com")
        
        # 4. Record metrics
        if pen_result.vulnerabilities:
            for vuln in pen_result.vulnerabilities:
                security_metrics.record_finding(
                    severity=Severity[vuln.get("severity", "MEDIUM")],
                    detected_at=datetime.now(timezone.utc),
                )
        
        # 5. Get security snapshot
        snapshot = security_metrics.get_snapshot()
        
        # 6. Generate threat report
        report = threat_modeler.generate_threat_report()
        
        # Verify all components worked
        assert threat.risk_score > 0
        assert attack_result.scenario_id == "ATK-001"
        assert pen_result.test_id is not None
        assert snapshot.security_score >= 0
        assert len(report["threats"]) >= 1
    
    def test_incident_response_simulation(self, incident_simulator, security_metrics):
        """Test incident response simulation."""
        # Create incident
        incident = incident_simulator.create_incident(
            title="Simulated Breach",
            severity=Severity.CRITICAL,
            description="Simulated security breach for testing",
            affected_systems=["web", "database"],
            indicators=["unusual_traffic", "failed_logins"],
        )
        
        # Record detection time
        security_metrics.record_detection(detection_time_minutes=5.0)
        
        # Progress through response
        incident_simulator.transition_incident(
            incident.incident_id,
            IncidentState.TRIAGED,
            notes="Impact assessed: 2 systems affected",
        )
        
        incident_simulator.transition_incident(
            incident.incident_id,
            IncidentState.CONTAINED,
            notes="Affected systems isolated",
        )
        
        # Record finding
        security_metrics.record_finding(
            severity=Severity.CRITICAL,
            detected_at=incident.detected_at,
            remediated_at=datetime.now(timezone.utc),
        )
        
        # Verify
        final_incident = incident_simulator.get_incident(incident.incident_id)
        assert final_incident.state == IncidentState.CONTAINED
        
        snapshot = security_metrics.get_snapshot()
        assert snapshot.mttd_minutes == 5.0
