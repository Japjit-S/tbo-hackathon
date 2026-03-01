"""
Transaction Processor - Orchestrates end-to-end transaction flow
3-step process: Evaluate → Execute → Update Trust
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from trust_manager import TrustManager
from booking_risk_evaluator import BookingRiskEvaluator, BookingRequest, BookingRiskAssessment


class TransactionProcessor:
    """
    Orchestrates complete transaction flow:
    1. Real-time risk evaluation
    2. Execute transaction (if approved)
    3. Update trust model based on outcome
    """

    def __init__(self, trust_manager: TrustManager):
        self.trust_mgr = trust_manager
        self.evaluator = BookingRiskEvaluator(trust_manager)
        self.transaction_log: List[Dict[str, Any]] = []

    def process_booking(self, agency_id: str, amount: float, location: str, notes: str = "") -> Dict[str, Any]:
        """
        Process booking: Evaluate → Execute → Update
        Returns full transaction record
        """
        booking_id = f"BUY_{agency_id}_{len(self.transaction_log) + 1}"
        
        # STEP 1: Evaluate risk
        request = BookingRequest(
            agency_id=agency_id,
            booking_id=booking_id,
            amount=amount,
            location=location
        )
        assessment = self.evaluator.evaluate(request)

        # STEP 2: Execute transaction (if approved)
        transaction_id = None
        if assessment.decision in ['approve', 'approve_with_monitoring']:
            transaction_id = f"TXN_{booking_id}_{datetime.now().timestamp()}"
            self.trust_mgr.db.save_transaction(
                transaction_id, agency_id, 'BOOKING', amount, 'APPROVED', notes
            )

        # STEP 3: Update trust model
        if assessment.decision == 'approve':
            self.trust_mgr.apply_positive_activity(agency_id, 'completed_booking', impact=1.0)
            credit_increase = 0.5
        elif assessment.decision == 'approve_with_monitoring':
            self.trust_mgr.apply_positive_activity(agency_id, 'completed_booking', impact=0.5)
            credit_increase = 0.25
        else:
            # Rejected transaction = incident
            if assessment.decision == 'restrict':
                self.trust_mgr.apply_incident(agency_id, 'high_velocity_booking', severity=0.8)
            credit_increase = -0.5

        record = {
            'booking_id': booking_id,
            'transaction_id': transaction_id,
            'amount': amount,
            'location': location,
            'decision': assessment.decision,
            'risk_score': assessment.risk_score,
            'trust_context': assessment.trust_context_score,
            'base_anomaly_score': assessment.base_anomaly_score,
            'evaluation_mode': assessment.evaluation_mode,
            'monthly_credit_limit': assessment.monthly_credit_limit,
            'exposure_ratio': assessment.exposure_ratio,
            'behavioral_anomalies': [(a.anomaly_type, a.severity, a.description) for a in assessment.behavioral_anomalies],
            'credit_increase_pct': credit_increase,
            'timestamp': datetime.now().isoformat(),
            'notes': notes,
            'reasoning': assessment.reasoning
        }

        self.transaction_log.append(record)
        return record

    def process_payment(self, agency_id: str, amount: float, notes: str = "") -> Dict[str, Any]:
        """
        Process payment: Reduce outstanding → Update trust
        Payments improve financial discipline
        """
        transaction_id = f"TXN_PAYMENT_{agency_id}_{datetime.now().timestamp()}"
        
        # Get current agency state
        agency = self.trust_mgr.get_agency(agency_id)
        if not agency:
            return {'error': 'Agency not found'}

        old_trust = agency.get_composite_trust_score()
        old_outstanding = agency.financial.outstanding_amount or 0.0

        # Reduce outstanding amount
        new_outstanding = max(0, old_outstanding - amount)
        agency.financial.outstanding_amount = new_outstanding

        # Improve financial metrics
        if amount > 0:
            # Increase on-time ratio (payments boost this)
            agency.financial.on_time_payment_ratio = min(100, agency.financial.on_time_payment_ratio + 5)
            # Reduce utilization
            agency.financial.credit_utilization_ratio = max(0, agency.financial.credit_utilization_ratio - 2)

        # Persist changes
        self.trust_mgr.db.save_agency(agency)
        self.trust_mgr.db.save_transaction(
            transaction_id, agency_id, 'PAYMENT', amount, 'PROCESSED', notes
        )

        new_trust = agency.get_composite_trust_score()
        trust_improvement = new_trust - old_trust

        record = {
            'transaction_id': transaction_id,
            'agency_id': agency_id,
            'amount': amount,
            'old_outstanding': old_outstanding,
            'new_outstanding': new_outstanding,
            'old_trust': old_trust,
            'new_trust': new_trust,
            'trust_improvement': trust_improvement,
            'timestamp': datetime.now().isoformat(),
            'notes': notes
        }

        self.transaction_log.append(record)
        return record

    def get_agency_status(self, agency_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive agency status"""
        return self.trust_mgr.get_agency_status(agency_id)

    def get_transaction_summary(self) -> Dict[str, Any]:
        """Get summary of all transactions"""
        return {
            'total_transactions': len(self.transaction_log),
            'transactions': self.transaction_log,
            'approvals': len([t for t in self.transaction_log if t.get('decision') == 'approve']),
            'rejections': len([t for t in self.transaction_log if t.get('decision') in ['reduce_exposure', 'escalate', 'restrict']])
        }

    def get_agency_transactions(self, agency_id: str) -> List[Dict[str, Any]]:
        """Get transactions for specific agency"""
        return [t for t in self.transaction_log if t.get('agency_id') == agency_id or t.get('booking_id', '').startswith(agency_id)]
