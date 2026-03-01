"""
Trust Manager - Facade linking TrustModel and Database
Provides high-level trust management operations
"""

from long_term_trust_model import LongTermTrustModel
from agency_database import AgencyDatabase
from agency_behavior_profile import AgencyBehaviorProfile, TransactionRecord
from typing import Optional, Dict, Any
from datetime import datetime


class TrustManager:
    """
    High-level facade for trust management.
    Coordinates between LongTermTrustModel and AgencyDatabase.
    """

    def __init__(self, db_path: str = "simulation.db"):
        self.db = AgencyDatabase(db_path)
        self.models: Dict[str, LongTermTrustModel] = {}  # In-memory cache

    def create_agency(self, agency_id: str) -> LongTermTrustModel:
        """Create new agency with baseline trust"""
        model = LongTermTrustModel(agency_id)
        self.models[agency_id] = model
        self.db.save_agency(model)
        return model

    def get_agency(self, agency_id: str) -> Optional[LongTermTrustModel]:
        """Get agency, loading from cache or database"""
        if agency_id in self.models:
            return self.models[agency_id]
        
        model = self.db.get_agency(agency_id)
        if model:
            self.models[agency_id] = model
        return model

    def update_financial_factors(self, agency_id: str, **kwargs):
        """Update financial factors and persist"""
        model = self.get_agency(agency_id)
        if model:
            model.update_financial_factors(**kwargs)
            self.db.save_agency(model)
            self.db.save_trust_snapshot(agency_id, model)

    def update_behavioral_factors(self, agency_id: str, **kwargs):
        """Update behavioral factors and persist"""
        model = self.get_agency(agency_id)
        if model:
            model.update_behavioral_factors(**kwargs)
            self.db.save_agency(model)
            self.db.save_trust_snapshot(agency_id, model)

    def update_operational_factors(self, agency_id: str, **kwargs):
        """Update operational factors and persist"""
        model = self.get_agency(agency_id)
        if model:
            model.update_operational_factors(**kwargs)
            self.db.save_agency(model)
            self.db.save_trust_snapshot(agency_id, model)

    def apply_positive_activity(self, agency_id: str, activity_type: str, impact: float = 1.0):
        """Apply positive activity boost"""
        model = self.get_agency(agency_id)
        if model:
            model.apply_positive_activity(activity_type, impact)
            self.db.save_agency(model)
            self.db.save_trust_snapshot(agency_id, model)

    def apply_incident(self, agency_id: str, incident_type: str, severity: float = 1.0):
        """Apply negative incident penalty"""
        model = self.get_agency(agency_id)
        if model:
            model.apply_negative_incident(incident_type, severity)
            self.db.save_agency(model)
            self.db.save_trust_snapshot(agency_id, model)

    def get_trust_score(self, agency_id: str) -> Optional[float]:
        """Get current trust score"""
        model = self.get_agency(agency_id)
        if model:
            return model.get_composite_trust_score()
        return None

    def get_trust_narrative(self, agency_id: str) -> Optional[str]:
        """Get detailed trust narrative"""
        model = self.get_agency(agency_id)
        if model:
            return model.get_trust_narrative()
        return None

    def get_agency_status(self, agency_id: str) -> Dict[str, Any]:
        """Get comprehensive agency status"""
        model = self.get_agency(agency_id)
        if not model:
            return {}

        return {
            'agency_id': agency_id,
            'trust_score': model.get_composite_trust_score(),
            'financial_score': model.financial.to_score(),
            'behavioral_score': model.behavioral.to_score(),
            'operational_score': model.operational.to_score(),
            'financial': {
                'on_time_ratio': model.financial.on_time_payment_ratio,
                'utilization': model.financial.credit_utilization_ratio,
                'outstanding': model.financial.outstanding_amount,
                'defaults': model.financial.default_history,
                'chargebacks': model.financial.chargeback_ratio,
            },
            'behavioral': {
                'frequency': model.behavioral.booking_frequency,
                'velocity': model.behavioral.velocity_spike_multiplier,
                'cancellation': model.behavioral.cancellation_ratio,
                'locations': model.behavioral.location_diversity,
                'trend': model.behavioral.booking_value_trend,
            },
            'operational': {
                'age_days': model.operational.account_age_days,
                'geos': model.operational.unique_geos,
                'verified': model.operational.document_verification,
                'registered': model.operational.registered_business,
                'contact_verified': model.operational.support_contact_verified,
            }
        }

    def generate_risk_report(self, agency_id: str) -> str:
        """Generate risk assessment report"""
        model = self.get_agency(agency_id)
        if not model:
            return "Agency not found"

        return model.get_trust_narrative()

    def get_agency_history(self, agency_id: str) -> list:
        """Get trust evolution history"""
        return self.db.get_agency_trust_history(agency_id)

    def get_agency_transactions(self, agency_id: str) -> list:
        """Get transaction history"""
        return self.db.get_agency_transactions(agency_id)

    def close(self):
        """Close database"""
        self.db.close()

    def calculate_and_save_risk_profile(self, agency_id: str) -> bool:
        """Calculate risk profile after month 1 (account age >= 30 days).
        Learns agency's personalized thresholds from transaction history."""
        model = self.get_agency(agency_id)
        if not model or model.operational.account_age_days < 30:
            return False

        month_number = (model.operational.account_age_days // 30) + 1
        
        # Get transaction history for this agency
        txn_history = self.db.get_agency_transactions(agency_id)
        
        # Calculate learned values
        booking_amounts = []
        booking_count = 0
        
        for txn in txn_history:
            if txn.get('type') == 'BOOKING':
                booking_amounts.append(txn.get('amount', 0))
                booking_count += 1
        
        # Learned average booking value
        avg_booking_value = sum(booking_amounts) / len(booking_amounts) if booking_amounts else 2500
        
        # Learned booking frequency (per week, approximate)
        days_active = max(1, model.operational.account_age_days)
        weeks_active = days_active / 7
        normal_frequency = booking_count / weeks_active if weeks_active > 0 else 1.0
        
        # Velocity threshold: learned multiplier (default 1.5x if no pattern yet)
        velocity_threshold = 1.5 if normal_frequency > 0 else 1.5
        
        # Signal weights (can be customized per signal as learned)
        signal_weights = {
            'velocity_spike': 0.8,
            'value_deviation': 0.6,
            'device_anomaly': 0.5,
            'credit_utilization': 0.7,
            'account_maturity': 0.3  # Less important in month 2+
        }
        
        profile_data = {
            'avg_booking_value': avg_booking_value,
            'normal_booking_frequency': normal_frequency,
            'velocity_threshold': velocity_threshold,
            'signal_weights': signal_weights
        }
        
        return self.db.save_risk_profile(agency_id, month_number, profile_data)

    def calculate_and_save_behavior_profile(self, agency_id: str) -> bool:
        """Calculate behavior profile from transaction history for anomaly detection"""
        model = self.get_agency(agency_id)
        if not model:
            return False

        # Get transaction history
        txn_history = self.db.get_agency_transactions(agency_id)
        
        if len(txn_history) < 3:
            return False  # Need minimum transactions to build profile
        
        # Create behavior profile
        behavior_profile = AgencyBehaviorProfile(agency_id)
        
        # Add transactions to profile
        for txn in txn_history:
            record = TransactionRecord(
                amount=txn.get('amount', 0),
                timestamp=datetime.fromisoformat(txn.get('timestamp', datetime.now().isoformat())),
                location=txn.get('location', 'US-CA'),
                booking_type=txn.get('type', 'BOOKING'),
                merchant_category=txn.get('merchant_category', 'TRAVEL')
            )
            behavior_profile.add_transaction(record)
        
        # Update statistics
        behavior_profile.update_statistics()
        
        # Save to database
        return self.db.save_behavior_profile(agency_id, behavior_profile.to_dict())
