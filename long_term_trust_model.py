"""
Long-Term Trust Model for B2B Travel Platform
Models agency trust evolution across 3 dimensions over time.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
import json
from calendar import monthrange


@dataclass
class FinancialDisciplineFactors:
    """Measures financial responsibility and payment reliability"""
    on_time_payment_ratio: float = 50.0  # 0-100: % of payments on time
    credit_utilization_ratio: float = 0.0  # 0-100: % of credit used
    outstanding_amount: float = 0.0  # $ amount outstanding
    default_history: int = 0  # count of defaults
    chargeback_ratio: float = 0.0  # 0-100: % of chargebacks
    next_payment_due_date: Optional[datetime] = None  # End of current month
    missed_payment_count: int = 0  # count of overdue payments

    def to_score(self) -> float:
        """Composite score 0-100"""
        on_time = self.on_time_payment_ratio * 0.45  # 45% weight
        utilization = (100 - self.credit_utilization_ratio) * 0.35  # Lower util is better, 35% weight
        no_defaults = max(0, 100 - (self.default_history * 15)) * 0.15  # Penalize defaults, 15% weight
        no_chargebacks = (100 - self.chargeback_ratio) * 0.05  # 5% weight
        return min(100, max(0, on_time + utilization + no_defaults + no_chargebacks))


@dataclass
class BehavioralStabilityFactors:
    """Measures booking patterns, velocity, and consistency"""
    booking_frequency: float = 0.0  # bookings per week
    velocity_spike_multiplier: float = 1.0  # 1.0 = normal, >1.5 = risky
    cancellation_ratio: float = 0.0  # 0-100: % of bookings cancelled
    location_diversity: int = 1  # count of unique locations booked
    booking_value_trend: str = "stable"  # stable, increasing, decreasing

    def to_score(self) -> float:
        """Composite score 0-100"""
        # Normal velocity is good, spikes reduce score
        velocity_penalty = max(0, (self.velocity_spike_multiplier - 1.0) * 25)
        velocity = max(0, 85 - velocity_penalty)

        # Frequency: higher is better (up to 100)
        frequency = min(100, self.booking_frequency * 15)

        # Lower cancellation is better
        cancellation = 100 - self.cancellation_ratio

        # Diversity helps: more locations = better (up to 25 points)
        diversity = min(25, self.location_diversity * 2.5)

        # Trend: increasing = +8, stable = 0, decreasing = -8
        trend_bonus = {"increasing": 8, "stable": 0, "decreasing": -8}.get(self.booking_value_trend, 0)

        return min(100, max(0, (velocity * 0.40 + frequency * 0.25 + cancellation * 0.25 + diversity * 0.10) / 1 + trend_bonus))


@dataclass
class OperationalLegitimacyFactors:
    """Measures account maturity, compliance, and legitimacy signals"""
    account_age_days: int = 0  # days since account creation
    unique_geos: List[str] = field(default_factory=lambda: ["US-CA"])  # locations
    document_verification: bool = False  # KYC/AML verified
    registered_business: bool = False  # Business registration verified
    support_contact_verified: bool = False  # Contact details verified
    api_usage: int = 0  # API calls made

    def to_score(self) -> float:
        """Composite score 0-100"""
        # Age: newer accounts are riskier
        # 0 days = 20, 30 days = 35, 90 days = 60, 180+ = 80
        age_score = min(100, (self.account_age_days / 3) + 20)

        # Verification points (max 30 points)
        verification_score = 0
        if self.document_verification:
            verification_score += 10
        if self.registered_business:
            verification_score += 10
        if self.support_contact_verified:
            verification_score += 10

        # Geo diversity: more locations = less suspicious (up to 20 points)
        geo_bonus = min(20, len(self.unique_geos) * 4)

        # API usage: some activity is good (not dormant) (up to 15 points)
        api_score = min(15, self.api_usage / 10)

        return min(100, max(0, age_score * 0.40 + verification_score * 0.30 + geo_bonus * 0.20 + api_score * 0.10))


@dataclass
class TrustSnapshot:
    """Captures trust state at a point in time"""
    timestamp: datetime
    financial_score: float
    behavioral_score: float
    operational_score: float
    composite_score: float
    notes: str = ""


class LongTermTrustModel:
    """
    Adaptive trust model that evolves based on agency behavior.
    Evaluates trust across 3 dimensions.
    """

    def __init__(self, agency_id: str):
        self.agency_id = agency_id
        self.created_at = datetime.now()
        
        # Initialize all factors to achieve composite score close to 55
        # Financial 60: on_time=60 → 60*0.45=27, util=50 → (100-50)*0.35=17.5, defaults=0 → 15, chargebacks=0 → 5 = 64.5
        # Behavioral 74: velocity=1.0 → 85*0.40=34, frequency=4.0 → 60*0.25=15, cancel=0 → 25, diversity=1 → 0.25 = 74.25
        # Operational 8.8: age=0 → 8, verification=0, geo=1 → 0.8, api=0 = 8.8
        # Composite: 64.5*0.40 + 74.25*0.35 + 8.8*0.25 = 25.8 + 26 + 2.2 = 54 (approximately)
        # Note: Score will actually be ~50-52 due to operational being low for new accounts
        self.financial = FinancialDisciplineFactors(
            on_time_payment_ratio=60.0,  # Baseline: 60% on-time payments
            credit_utilization_ratio=50.0,  # Neutral usage
            outstanding_amount=0.0,
            default_history=0,
            chargeback_ratio=0.0,
            next_payment_due_date=None,
            missed_payment_count=0
        )
        self.behavioral = BehavioralStabilityFactors(
            booking_frequency=4.0,  # Baseline: 4 bookings per week
            velocity_spike_multiplier=1.0,
            cancellation_ratio=0.0,
            location_diversity=1,
            booking_value_trend="stable"
        )
        self.operational = OperationalLegitimacyFactors(
            account_age_days=0,
            unique_geos=["US-CA"],
            document_verification=False,
            registered_business=False,
            support_contact_verified=False,
            api_usage=0
        )
        
        self.snapshots: List[TrustSnapshot] = []
        self._snapshot_at_creation()

    def _snapshot_at_creation(self):
        """Create initial snapshot"""
        snapshot = TrustSnapshot(
            timestamp=self.created_at,
            financial_score=self.financial.to_score(),
            behavioral_score=self.behavioral.to_score(),
            operational_score=self.operational.to_score(),
            composite_score=self.get_composite_trust_score(),
            notes="Account created"
        )
        self.snapshots.append(snapshot)

    def get_composite_trust_score(self) -> float:
        """Calculate weighted composite score: Financial 40%, Behavioral 35%, Operational 25%"""
        financial_score = self.financial.to_score()
        behavioral_score = self.behavioral.to_score()
        operational_score = self.operational.to_score()
        
        return (
            financial_score * 0.40 +
            behavioral_score * 0.35 +
            operational_score * 0.25
        )

    def get_monthly_credit_limit(self) -> float:
        """Calculate monthly credit limit based on composite trust score.
        Formula: 5000 + ((score - 55) / 5) * 5000
        Score 55 = $5,000, +$5,000 per 5 points"""
        composite_score = self.get_composite_trust_score()
        base_limit = 5000.0
        points_above_base = max(0, composite_score - 55)
        increment_multiplier = points_above_base / 5
        monthly_limit = base_limit + (increment_multiplier * 5000)
        return max(base_limit, monthly_limit)

    def get_exposure_ratio(self) -> float:
        """Calculate exposure ratio: outstanding / monthly_credit_limit.
        Returns 0-1 (0% to 100%)"""
        monthly_limit = self.get_monthly_credit_limit()
        if monthly_limit <= 0:
            return 0.0
        outstanding = self.financial.outstanding_amount or 0.0
        exposure = outstanding / monthly_limit
        return min(1.0, max(0.0, exposure))

    def get_next_payment_due_date(self, current_date: Optional[datetime] = None) -> datetime:
        """Calculate next payment due date (end of current month).
        If no date provided, uses today."""
        if current_date is None:
            current_date = datetime.now()
        
        # Get the last day of the current month
        _, last_day = monthrange(current_date.year, current_date.month)
        due_date = datetime(current_date.year, current_date.month, last_day, 23, 59, 59)
        
        return due_date

    def is_payment_overdue(self, current_date: Optional[datetime] = None) -> bool:
        """Check if payment is overdue.
        A payment is overdue if current date is past the due date and amount is outstanding."""
        if self.financial.outstanding_amount <= 0:
            return False
        
        if self.financial.next_payment_due_date is None:
            return False
        
        if current_date is None:
            current_date = datetime.now()
        
        return current_date > self.financial.next_payment_due_date

    def update_financial_factors(self, **kwargs):
        """Update financial discipline factors"""
        for key, value in kwargs.items():
            if hasattr(self.financial, key):
                setattr(self.financial, key, value)

    def update_behavioral_factors(self, **kwargs):
        """Update behavioral stability factors"""
        for key, value in kwargs.items():
            if hasattr(self.behavioral, key):
                setattr(self.behavioral, key, value)

    def update_operational_factors(self, **kwargs):
        """Update operational legitimacy factors"""
        for key, value in kwargs.items():
            if hasattr(self.operational, key):
                setattr(self.operational, key, value)

    def apply_positive_activity(self, activity_type: str, impact: float = 1.0):
        """Boost trust based on positive activity"""
        if activity_type == "on_time_payment":
            self.financial.on_time_payment_ratio = min(100, self.financial.on_time_payment_ratio + (2 * impact))
        elif activity_type == "completed_booking":
            self.behavioral.booking_frequency = min(10, self.behavioral.booking_frequency + (0.5 * impact))
        elif activity_type == "verified_document":
            self.operational.document_verification = True
        elif activity_type == "registered_business":
            self.operational.registered_business = True

    def apply_negative_incident(self, incident_type: str, severity: float = 1.0):
        """Reduce trust based on negative incident"""
        severity = min(1.0, max(0.0, severity))  # Normalize to 0-1
        
        if incident_type == "missed_payment":
            self.financial.on_time_payment_ratio = max(0, self.financial.on_time_payment_ratio - (5 * severity))
        elif incident_type == "chargeback":
            self.financial.chargeback_ratio = min(100, self.financial.chargeback_ratio + (10 * severity))
        elif incident_type == "high_velocity_booking":
            self.behavioral.velocity_spike_multiplier = 1.0 + (1.5 * severity)
        elif incident_type == "booking_cancellation":
            self.behavioral.cancellation_ratio = min(100, self.behavioral.cancellation_ratio + (5 * severity))
        elif incident_type == "fraud_detection":
            self.behavioral.velocity_spike_multiplier = 2.0 + (1.0 * severity)
            self.financial.default_history += 1

    def add_snapshot(self, notes: str = ""):
        """Create a trust snapshot (for historical tracking)"""
        snapshot = TrustSnapshot(
            timestamp=datetime.now(),
            financial_score=self.financial.to_score(),
            behavioral_score=self.behavioral.to_score(),
            operational_score=self.operational.to_score(),
            composite_score=self.get_composite_trust_score(),
            notes=notes
        )
        self.snapshots.append(snapshot)
        return snapshot

    def get_trust_narrative(self) -> str:
        """Generate human-readable trust assessment"""
        score = self.get_composite_trust_score()
        
        if score >= 80:
            risk_level = "✓ LOW RISK"
        elif score >= 60:
            risk_level = "⚠ MODERATE RISK"
        elif score >= 40:
            risk_level = "⚠⚠ HIGH RISK"
        else:
            risk_level = "🚨 CRITICAL RISK"

        financial = self.financial.to_score()
        behavioral = self.behavioral.to_score()
        operational = self.operational.to_score()

        narrative = f"""
TRUST ASSESSMENT: {self.agency_id}
{'='*50}
Overall Trust Score: {score:.2f}/100 [{risk_level}]

Dimension Breakdown:
  Financial Discipline:    {financial:.2f}/100
    • On-time ratio: {self.financial.on_time_payment_ratio:.1f}%
    • Credit utilization: {self.financial.credit_utilization_ratio:.1f}%
    • Outstanding: ${self.financial.outstanding_amount:,.2f}
    • Chargebacks: {self.financial.chargeback_ratio:.1f}%
    • Defaults: {self.financial.default_history}

  Behavioral Stability:    {behavioral:.2f}/100
    • Booking frequency: {self.behavioral.booking_frequency:.2f}/week
    • Velocity multiplier: {self.behavioral.velocity_spike_multiplier:.2f}x
    • Cancellation rate: {self.behavioral.cancellation_ratio:.1f}%
    • Unique locations: {self.behavioral.location_diversity}
    • Value trend: {self.behavioral.booking_value_trend}

  Operational Legitimacy: {operational:.2f}/100
    • Account age: {self.operational.account_age_days} days
    • Verified: {self.operational.document_verification}
    • Registered: {self.operational.registered_business}
    • Contact verified: {self.operational.support_contact_verified}
    • Unique geos: {', '.join(self.operational.unique_geos)}
"""
        return narrative

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            'agency_id': self.agency_id,
            'created_at': self.created_at.isoformat(),
            'financial': asdict(self.financial),
            'behavioral': asdict(self.behavioral),
            'operational': {
                'account_age_days': self.operational.account_age_days,
                'unique_geos': self.operational.unique_geos,
                'document_verification': self.operational.document_verification,
                'registered_business': self.operational.registered_business,
                'support_contact_verified': self.operational.support_contact_verified,
                'api_usage': self.operational.api_usage,
            },
            'composite_score': self.get_composite_trust_score(),
            'snapshot_count': len(self.snapshots)
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'LongTermTrustModel':
        """Deserialize from dictionary"""
        model = LongTermTrustModel(data['agency_id'])
        model.created_at = datetime.fromisoformat(data['created_at'])
        
        # Restore financial factors
        for key, value in data['financial'].items():
            setattr(model.financial, key, value)
        
        # Restore behavioral factors
        for key, value in data['behavioral'].items():
            setattr(model.behavioral, key, value)
        
        # Restore operational factors
        for key, value in data['operational'].items():
            setattr(model.operational, key, value)
        
        return model
