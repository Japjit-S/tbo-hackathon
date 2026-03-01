"""
Real-time Booking Risk Evaluator
Evaluates booking requests using behavioral anomaly detection + trust context
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from trust_manager import TrustManager
from agency_behavior_profile import AgencyBehaviorProfile, TransactionRecord
from datetime import datetime


@dataclass
class BookingRequest:
    """Incoming booking request to evaluate"""
    agency_id: str
    booking_id: str
    amount: float
    location: str
    device_id: str = "DEV_web_001"
    timestamp: datetime = field(default_factory=datetime.now)
    merchant_category: str = "TRAVEL"


@dataclass
class RiskSignal:
    """Single risk signal detected"""
    signal_type: str
    severity: float  # 0-1
    description: str


@dataclass
class BehavioralAnomaly:
    """Behavioral anomaly detected"""
    anomaly_type: str
    severity: float  # 0-1
    description: str


@dataclass
class BookingRiskAssessment:
    """Result of risk evaluation"""
    booking_id: str
    risk_score: float  # 0-100
    decision: str  # approve, approve_with_monitoring, reduce_exposure, escalate, restrict
    confidence: float  # 0-100
    risk_signals: List[RiskSignal] = field(default_factory=list)
    behavioral_anomalies: List[BehavioralAnomaly] = field(default_factory=list)
    trust_context_score: float = 0.0
    base_anomaly_score: float = 0.0
    reasoning: str = ""
    evaluation_mode: str = "BASELINE"  # BASELINE or PERSONALIZED
    monthly_credit_limit: float = 5000.0
    exposure_ratio: float = 0.0


class BookingRiskEvaluator:
    """
    Real-time risk evaluator for booking requests.
    Uses trust context + multiple risk signals.
    Switches to personalized evaluation after month 1 (30+ days).
    """

    def __init__(self, trust_manager: TrustManager):
        self.trust_mgr = trust_manager
        self.risk_thresholds = {
            'approve': 20,           # < 20
            'monitor': 35,           # 20-35
            'reduce': 50,            # 35-50
            'escalate': 65,          # 50-65
            'restrict': 100          # > 65
        }

    def _get_evaluation_mode(self, agency_model) -> str:
        """Determine if using baseline or personalized evaluation.
        Baseline (Month 1): account_age_days < 30
        Personalized (Month 2+): account_age_days >= 30"""
        if agency_model.operational.account_age_days < 30:
            return "BASELINE"
        else:
            return "PERSONALIZED"

    def _get_month_number(self, account_age_days: int) -> int:
        """Calculate month number from account age.
        Month 1: 0-29 days, Month 2: 30-59 days, etc."""
        return (account_age_days // 30) + 1

    def evaluate(self, booking_request: BookingRequest) -> BookingRiskAssessment:
        """Evaluate booking risk using behavioral + trust context"""
        # Get trust context
        trust_score = self.trust_mgr.get_trust_score(booking_request.agency_id)
        agency_model = self.trust_mgr.get_agency(booking_request.agency_id)
        
        if not agency_model:
            # Unknown agency = high risk
            return BookingRiskAssessment(
                booking_id=booking_request.booking_id,
                risk_score=75.0,
                decision='restrict',
                confidence=100.0,
                trust_context_score=0.0,
                reasoning="Agency not found in system",
                evaluation_mode="BASELINE",
                monthly_credit_limit=5000.0,
                exposure_ratio=0.0
            )

        trust_score = trust_score or 50.0  # Default to neutral if None
        
        # Determine evaluation mode
        evaluation_mode = self._get_evaluation_mode(agency_model)
        monthly_credit_limit = agency_model.get_monthly_credit_limit()
        exposure_ratio = agency_model.get_exposure_ratio()

        # Load or initialize behavior profile
        behavior_profile = AgencyBehaviorProfile(booking_request.agency_id)
        behavior_data = self.trust_mgr.db.get_behavior_profile(booking_request.agency_id)
        if behavior_data:
            behavior_profile = AgencyBehaviorProfile.from_dict(behavior_data)

        # Detect traditional risk signals
        signals = self._detect_risk_signals(booking_request, agency_model)
        
        # Detect behavioral anomalies
        behavioral_anomalies = self._detect_behavioral_anomalies(booking_request, behavior_profile)
        
        # Calculate base anomaly score from behavioral anomalies
        base_anomaly_score = 0.0
        if behavioral_anomalies:
            avg_anomaly = sum(a.severity for a in behavioral_anomalies) / len(behavioral_anomalies)
            base_anomaly_score = avg_anomaly * 100
        
        # Calculate risk score with new formula
        risk_score = self._calculate_risk_score(signals, trust_score, base_anomaly_score)

        # Make decision
        decision = self._make_decision(risk_score, trust_score, signals)

        # Calculate confidence
        confidence = self._calculate_confidence(risk_score, len(signals) + len(behavioral_anomalies))

        # Build reasoning
        reasoning = self._build_reasoning(signals, behavioral_anomalies, trust_score, decision, evaluation_mode)

        return BookingRiskAssessment(
            booking_id=booking_request.booking_id,
            risk_score=risk_score,
            decision=decision,
            confidence=confidence,
            risk_signals=signals,
            behavioral_anomalies=behavioral_anomalies,
            trust_context_score=trust_score,
            base_anomaly_score=base_anomaly_score,
            reasoning=reasoning,
            evaluation_mode=evaluation_mode,
            monthly_credit_limit=monthly_credit_limit,
            exposure_ratio=exposure_ratio
        )

    def _detect_risk_signals(self, request: BookingRequest, agency_model) -> List[RiskSignal]:
        """Detect all risk signals present"""
        signals = []

        # Signal 1: Velocity spike
        if agency_model.behavioral.velocity_spike_multiplier > 1.5:
            severity = min(1.0, (agency_model.behavioral.velocity_spike_multiplier - 1.0) / 2.0)
            signals.append(RiskSignal(
                signal_type='velocity_spike',
                severity=severity,
                description=f"High velocity spike: {agency_model.behavioral.velocity_spike_multiplier:.2f}x"
            ))

        # Signal 2: Unusual booking value
        avg_value = 2500  # Assumed average booking
        if request.amount > avg_value * 3:
            severity = min(1.0, (request.amount / avg_value - 1.0) / 5.0)
            signals.append(RiskSignal(
                signal_type='value_deviation',
                severity=severity,
                description=f"Unusually high booking: ${request.amount:,.0f}"
            ))
        elif request.amount < avg_value * 0.1:
            severity = 0.2
            signals.append(RiskSignal(
                signal_type='value_deviation',
                severity=severity,
                description=f"Unusually low booking: ${request.amount:,.0f}"
            ))

        # Signal 3: Device anomaly
        if request.device_id not in ['DEV_web_001', 'DEV_mobile_001', 'DEV_api_001']:
            signals.append(RiskSignal(
                signal_type='device_anomaly',
                severity=0.3,
                description=f"Unknown device: {request.device_id}"
            ))

        # Signal 4: Credit utilization high
        if agency_model.financial.credit_utilization_ratio > 80:
            severity = min(1.0, (agency_model.financial.credit_utilization_ratio - 50) / 50)
            signals.append(RiskSignal(
                signal_type='credit_utilization',
                severity=severity,
                description=f"High credit utilization: {agency_model.financial.credit_utilization_ratio:.1f}%"
            ))

        # Signal 5: Account maturity (new accounts are riskier)
        account_age = agency_model.operational.account_age_days
        if account_age < 30:
            severity = max(0.1, 1.0 - (account_age / 30))
            signals.append(RiskSignal(
                signal_type='account_maturity',
                severity=severity,
                description=f"New account ({account_age} days old)"
            ))

        return signals

    def _detect_behavioral_anomalies(self, request: BookingRequest, behavior_profile: AgencyBehaviorProfile) -> List[BehavioralAnomaly]:
        """Detect behavioral anomalies using learned patterns"""
        anomalies = []
        
        if not behavior_profile.is_learned():
            return anomalies  # Not enough data yet
        
        # Anomaly 1: Amount deviation
        amount_dev = behavior_profile.calculate_amount_deviation(request.amount)
        if amount_dev > 0.3:
            anomalies.append(BehavioralAnomaly(
                anomaly_type='amount_deviation',
                severity=amount_dev,
                description=f"Amount ${request.amount:,.0f} is {amount_dev*100:.0f}% unusual (avg: ${behavior_profile.avg_booking_amount:,.0f})"
            ))
        
        # Anomaly 2: Timing anomaly
        timing_anomaly = behavior_profile.is_timing_anomaly(request.timestamp)
        if timing_anomaly > 0.5:
            anomalies.append(BehavioralAnomaly(
                anomaly_type='timing_anomaly',
                severity=timing_anomaly,
                description=f"Booking at {request.timestamp.strftime('%H:%M')} is unusual for this agency"
            ))
        
        # Anomaly 3: Geographic anomaly
        geo_anomaly = behavior_profile.is_geo_anomaly(request.location)
        if geo_anomaly > 0.5:
            anomalies.append(BehavioralAnomaly(
                anomaly_type='geo_anomaly',
                severity=geo_anomaly,
                description=f"Location {request.location} is outside known geos: {behavior_profile.known_geos}"
            ))
        
        # Anomaly 4: Pattern break
        pattern_break = behavior_profile.calculate_pattern_break(request.amount)
        if pattern_break > 0.4:
            recent_avg = sum(behavior_profile.recent_booking_amounts) / max(1, len(behavior_profile.recent_booking_amounts))
            anomalies.append(BehavioralAnomaly(
                anomaly_type='pattern_break',
                severity=pattern_break,
                description=f"Amount breaks recent pattern (recent avg: ${recent_avg:,.0f})"
            ))
        
        # Anomaly 5: Exposure velocity
        exposure_velocity = behavior_profile.calculate_exposure_velocity(
            behavior_profile.booking_amounts[-1] if behavior_profile.booking_amounts else 0,  # Placeholder
            5000 * ((sum(behavior_profile.booking_amounts) / max(1, len(behavior_profile.booking_amounts))) / 55)  # Placeholder limit
        )
        if exposure_velocity > 0.5:
            anomalies.append(BehavioralAnomaly(
                anomaly_type='exposure_velocity',
                severity=exposure_velocity,
                description=f"Credit exposure growing at {exposure_velocity*100:.0f}% pace"
            ))
        
        return anomalies

    def _calculate_risk_score(self, signals: List[RiskSignal], trust_score: float, base_anomaly_score: float = 0.0) -> float:
        """
        Calculate overall risk score using behavioral anomalies + trust context.
        
        Formula:
        risk = (base_anomaly * 0.40) + (trust_modifier * 0.35) + (fraud_signals * 0.25)
        
        where:
        - base_anomaly: behavioral deviations (0-100)
        - trust_modifier: (100 - trust_score) * 0.7 (inverse of trust)
        - fraud_signals: specific fraud indicators from signals (0-100)
        """
        # Base anomaly score (0-100)
        anomaly_component = base_anomaly_score
        
        # Trust modifier component: lower trust = higher risk
        trust_modifier = (100 - trust_score) * 0.7
        
        # Fraud signals component: aggregate signal severities
        signal_risk = 0.0
        if signals:
            avg_signal_severity = sum(s.severity for s in signals) / len(signals)
            signal_risk = avg_signal_severity * 100  # Convert to 0-100
        
        # Combined risk score
        total_risk = (anomaly_component * 0.40) + (trust_modifier * 0.35) + (signal_risk * 0.25)
        
        return min(100, max(0, total_risk))

    def _make_decision(self, risk_score: float, trust_score: float, signals: List[RiskSignal]) -> str:
        """Make approval decision based on risk score"""
        # High trust overrides moderate risk
        if trust_score >= 90 and risk_score < 40:
            return 'approve'

        if risk_score < self.risk_thresholds['approve']:
            return 'approve'
        elif risk_score < self.risk_thresholds['monitor']:
            return 'approve_with_monitoring'
        elif risk_score < self.risk_thresholds['reduce']:
            return 'reduce_exposure'
        elif risk_score < self.risk_thresholds['escalate']:
            return 'escalate'
        else:
            return 'restrict'

    def _calculate_confidence(self, risk_score: float, signal_count: int) -> float:
        """Calculate confidence in decision 0-100"""
        # More signals = higher confidence in assessment
        signal_confidence = min(100, 50 + (signal_count * 10))

        # Extreme scores = higher confidence
        if risk_score < 10 or risk_score > 90:
            return 100.0

        return signal_confidence

    def _build_reasoning(self, signals: List[RiskSignal], behavioral_anomalies: List[BehavioralAnomaly], trust_score: float, decision: str, evaluation_mode: str = "BASELINE") -> str:
        """Build human-readable decision reasoning"""
        if trust_score >= 80:
            trust_statement = "✓ Agency has high trust profile"
        elif trust_score >= 60:
            trust_statement = "⚠ Agency has moderate trust profile"
        else:
            trust_statement = "🚨 Agency has low trust profile"

        signal_text = ""
        if signals:
            signal_text = f"\nTraditional Risk Signals ({len(signals)}):\n"
            for sig in signals:
                signal_text += f"  • {sig.signal_type}: {sig.description}\n"

        anomaly_text = ""
        if behavioral_anomalies:
            anomaly_text = f"\nBehavioral Anomalies ({len(behavioral_anomalies)}):\n"
            for anom in behavioral_anomalies:
                anomaly_text += f"  • {anom.anomaly_type}: {anom.description}\n"

        decision_map = {
            'approve': 'Approve booking - Low risk profile\nConsider increasing credit limit by 0.5%',
            'approve_with_monitoring': 'Approve with enhanced monitoring\nFlag for post-transaction review',
            'reduce_exposure': 'Reduce exposure on this booking\nCap transaction at 50% of normal limit',
            'escalate': 'Escalate for manual review\nRisk indicators warrant investigation',
            'restrict': 'Restrict booking - High risk detected\nBlock transaction and notify compliance'
        }

        mode_text = f"Evaluation Mode: {evaluation_mode} - "
        if evaluation_mode == "BASELINE":
            mode_text += "Using generic thresholds (Month 1)"
        else:
            mode_text += "Using personalized thresholds (Month 2+)"

        reasoning = f"{mode_text}\n{trust_statement}{signal_text}{anomaly_text}\nDECISION: {decision_map.get(decision, 'Unknown decision')}"
        return reasoning
