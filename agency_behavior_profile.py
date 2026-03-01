"""
Agency Behavior Profile - Tracks behavioral patterns for anomaly detection
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Dict, Any, Set
from collections import deque
import statistics


@dataclass
class TransactionRecord:
    """Single transaction for pattern analysis"""
    amount: float
    timestamp: datetime
    location: str
    booking_type: str  # 'BOOKING' or 'PAYMENT'
    merchant_category: str = "TRAVEL"


class AgencyBehaviorProfile:
    """
    Learns and tracks agency behavior patterns for real-time anomaly detection.
    Used to identify if current transaction is unusual for this agency.
    """

    def __init__(self, agency_id: str):
        self.agency_id = agency_id
        
        # Transaction amount statistics
        self.booking_amounts: List[float] = []
        self.avg_booking_amount: float = 0.0
        self.std_dev_booking_amount: float = 0.0
        self.min_booking_amount: float = 0.0
        self.max_booking_amount: float = 0.0
        
        # Transaction frequency
        self.booking_frequency_per_week: float = 0.0  # bookings/week
        self.avg_days_between_bookings: float = 0.0
        self.std_dev_days_between_bookings: float = 0.0
        
        # Timing patterns (hour of day when they typically book)
        self.typical_booking_hours: Set[int] = set(range(9, 18))  # Default: 9 AM - 6 PM
        self.booking_hours_histogram: Dict[int, int] = {}
        
        # Geographic patterns
        self.known_geos: Set[str] = {"US-CA"}  # Locations they typically book
        self.geo_distribution: Dict[str, float] = {}  # Geo -> % of bookings
        
        # Recent transactions (last 20)
        self.recent_transactions: deque = deque(maxlen=20)
        self.recent_booking_amounts: deque = deque(maxlen=10)
        
        # Payment patterns
        self.avg_payment_recovery_days: float = 0.0  # Days to pay off booking
        self.std_dev_recovery_days: float = 0.0
        self.recovery_times: List[float] = []
        
        # Booking vs Payment ratio
        self.booking_payment_ratio: float = 0.5  # Avg ratio of bookings to payments
        
        # Merchant categories they typically use
        self.merchant_categories: Set[str] = {"TRAVEL"}
        
        # Transaction size trend (increasing, stable, decreasing)
        self.size_trend: str = "stable"
        
        # Days since last transaction
        self.last_transaction_date: datetime = datetime.now()
        self.days_since_last_transaction: int = 0
        
        # Learning threshold (need min transactions before anomaly detection works)
        self.min_transactions_for_learning: int = 5
        self.transaction_count: int = 0

    def add_transaction(self, transaction: TransactionRecord) -> None:
        """Add transaction to profile and update statistics"""
        self.recent_transactions.append(transaction)
        self.transaction_count += 1
        
        if transaction.booking_type == "BOOKING":
            self.booking_amounts.append(transaction.amount)
            self.recent_booking_amounts.append(transaction.amount)
            
            # Update geo distribution
            if transaction.location not in self.known_geos:
                self.known_geos.add(transaction.location)
            
            # Update merchant category
            if transaction.merchant_category not in self.merchant_categories:
                self.merchant_categories.add(transaction.merchant_category)
            
            # Track booking time
            booking_hour = transaction.timestamp.hour
            self.booking_hours_histogram[booking_hour] = self.booking_hours_histogram.get(booking_hour, 0) + 1
        
        # Update last transaction date
        self.last_transaction_date = transaction.timestamp

    def update_statistics(self) -> None:
        """Recalculate all statistics from transaction history"""
        if not self.booking_amounts:
            return
        
        # Amount statistics
        self.avg_booking_amount = statistics.mean(self.booking_amounts)
        self.min_booking_amount = min(self.booking_amounts)
        self.max_booking_amount = max(self.booking_amounts)
        
        if len(self.booking_amounts) > 1:
            self.std_dev_booking_amount = statistics.stdev(self.booking_amounts)
        else:
            self.std_dev_booking_amount = 0.0
        
        # Geographic distribution
        total_bookings = len(self.booking_amounts)
        self.geo_distribution = {
            geo: (sum(1 for t in self.recent_transactions if t.location == geo) / max(1, total_bookings))
            for geo in self.known_geos
        }
        
        # Typical booking hours (hours with > 1 booking)
        self.typical_booking_hours = {
            hour for hour, count in self.booking_hours_histogram.items() if count >= 1
        }
        
        # Frequency: bookings per week
        if len(self.recent_transactions) > 1:
            days_span = (self.recent_transactions[-1].timestamp - self.recent_transactions[0].timestamp).days
            weeks_span = max(1, days_span / 7)
            self.booking_frequency_per_week = len([t for t in self.recent_transactions if t.booking_type == "BOOKING"]) / weeks_span
        
        # Size trend (compare recent to historical)
        if len(self.booking_amounts) > 5:
            recent_avg = statistics.mean(list(self.recent_booking_amounts)[-5:])
            historical_avg = statistics.mean(self.booking_amounts[:-5])
            
            if recent_avg > historical_avg * 1.1:
                self.size_trend = "increasing"
            elif recent_avg < historical_avg * 0.9:
                self.size_trend = "decreasing"
            else:
                self.size_trend = "stable"

    def is_learned(self) -> bool:
        """Check if profile has enough data for reliable anomaly detection"""
        return self.transaction_count >= self.min_transactions_for_learning

    def calculate_amount_deviation(self, amount: float) -> float:
        """
        Calculate how much this amount deviates from normal.
        Returns normalized deviation 0-1.
        """
        if not self.is_learned() or self.std_dev_booking_amount == 0:
            return 0.0
        
        z_score = abs((amount - self.avg_booking_amount) / max(self.std_dev_booking_amount, 0.1))
        # Z-score of 3 = 3 std devs away, normalize to 0-1
        deviation = min(1.0, z_score / 3.0)
        return deviation

    def calculate_frequency_deviation(self, current_frequency: float) -> float:
        """
        Calculate if booking frequency is unusual.
        Returns 0-1 (0 = normal, 1 = very unusual).
        """
        if not self.is_learned() or self.booking_frequency_per_week == 0:
            return 0.0
        
        frequency_ratio = current_frequency / max(self.booking_frequency_per_week, 0.1)
        # Ratio > 2x or < 0.5x is unusual
        if frequency_ratio > 2.0:
            return min(1.0, (frequency_ratio - 2.0) / 2.0)
        elif frequency_ratio < 0.5:
            return min(1.0, (0.5 - frequency_ratio) / 0.5)
        else:
            return 0.0

    def is_timing_anomaly(self, timestamp: datetime) -> float:
        """
        Check if booking is at unusual time.
        Returns 0.0 (normal) or 1.0 (anomaly).
        """
        if not self.is_learned():
            return 0.0
        
        booking_hour = timestamp.hour
        if booking_hour not in self.typical_booking_hours:
            return 1.0
        return 0.0

    def is_geo_anomaly(self, location: str) -> float:
        """
        Check if location is outside known geos.
        Returns 0.0 (known) or 1.0 (unknown).
        """
        if location in self.known_geos:
            return 0.0
        return 1.0

    def calculate_pattern_break(self, new_amount: float) -> float:
        """
        Check if this amount breaks recent transaction pattern.
        Compares to last 5 transactions.
        Returns 0-1 (0 = consistent, 1 = breaks pattern).
        """
        if len(self.recent_booking_amounts) < 3:
            return 0.0
        
        recent_avg = statistics.mean(list(self.recent_booking_amounts)[-5:])
        recent_std = statistics.stdev(list(self.recent_booking_amounts)[-5:]) if len(list(self.recent_booking_amounts)[-5:]) > 1 else 0.1
        
        z_score = abs((new_amount - recent_avg) / max(recent_std, 0.1))
        pattern_break = min(1.0, z_score / 2.0)  # 2 std devs = 1.0 pattern break
        return pattern_break

    def calculate_exposure_velocity(self, current_outstanding: float, monthly_limit: float) -> float:
        """
        Check if exposure is growing faster than usual.
        Returns 0-1 (0 = normal pace, 1 = very fast).
        """
        if not self.is_learned() or monthly_limit <= 0:
            return 0.0
        
        current_exposure = current_outstanding / monthly_limit
        
        # If exposure < 20%, it's normal pace
        # If exposure > 70%, it's risky pace
        if current_exposure < 0.2:
            return 0.0
        elif current_exposure > 0.7:
            return min(1.0, (current_exposure - 0.7) / 0.3)
        else:
            return (current_exposure - 0.2) / 0.5

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for database storage"""
        return {
            'agency_id': self.agency_id,
            'avg_booking_amount': self.avg_booking_amount,
            'std_dev_booking_amount': self.std_dev_booking_amount,
            'min_booking_amount': self.min_booking_amount,
            'max_booking_amount': self.max_booking_amount,
            'booking_frequency_per_week': self.booking_frequency_per_week,
            'avg_days_between_bookings': self.avg_days_between_bookings,
            'known_geos': list(self.known_geos),
            'merchant_categories': list(self.merchant_categories),
            'typical_booking_hours': list(self.typical_booking_hours),
            'avg_payment_recovery_days': self.avg_payment_recovery_days,
            'booking_payment_ratio': self.booking_payment_ratio,
            'size_trend': self.size_trend,
            'transaction_count': self.transaction_count
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'AgencyBehaviorProfile':
        """Deserialize from dictionary"""
        profile = AgencyBehaviorProfile(data['agency_id'])
        profile.avg_booking_amount = data.get('avg_booking_amount', 0.0)
        profile.std_dev_booking_amount = data.get('std_dev_booking_amount', 0.0)
        profile.min_booking_amount = data.get('min_booking_amount', 0.0)
        profile.max_booking_amount = data.get('max_booking_amount', 0.0)
        profile.booking_frequency_per_week = data.get('booking_frequency_per_week', 0.0)
        profile.known_geos = set(data.get('known_geos', ['US-CA']))
        profile.merchant_categories = set(data.get('merchant_categories', ['TRAVEL']))
        profile.typical_booking_hours = set(data.get('typical_booking_hours', range(9, 18)))
        profile.avg_payment_recovery_days = data.get('avg_payment_recovery_days', 0.0)
        profile.booking_payment_ratio = data.get('booking_payment_ratio', 0.5)
        profile.size_trend = data.get('size_trend', 'stable')
        profile.transaction_count = data.get('transaction_count', 0)
        return profile
