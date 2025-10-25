"""
Anti-FOMO Manager - Prevents emotional/rushed trading

Detects and blocks FOMO (Fear Of Missing Out) trades before entry.

FOMO Signals:
1. Setup incomplete (missing conditions)
2. Price chasing (too far from zone)
3. Skipped fibonacci (no retest)
4. Rapid entry (too fast after last trade)
5. Volatility spike (ATR doubled)
6. Low patience (emotional state)
"""

from __future__ import annotations
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class SetupData:
    """Setup kalitesi ve durumu"""
    # PA conditions
    zone: Optional[Dict] = None
    choch: Optional[Dict] = None
    fib_retest: Optional[Dict] = None
    
    # Prices
    zone_price: float = 0.0
    current_price: float = 0.0
    entry_price: float = 0.0
    
    # Quality
    setup_score: float = 0.0
    zone_quality: float = 0.0
    choch_strength: float = 0.0
    
    # Timing
    candles_since_setup: int = 0
    setup_age_minutes: int = 0
    
    # Market conditions
    atr_percent: float = 0.0
    atr_change_percent: float = 0.0  # ATR change from baseline
    volume_ratio: float = 1.0


@dataclass
class BotState:
    """Bot'un psikolojik durumu"""
    # Emotional state
    confidence: float = 0.5  # 0.0-1.0
    stress: float = 0.0      # 0.0-1.0
    patience: float = 1.0    # 0.0-1.0
    
    # Recent activity
    last_trade_time: Optional[datetime] = None
    minutes_since_last_trade: int = 999
    
    # Performance
    recent_win_rate: float = 0.5
    consecutive_losses: int = 0
    consecutive_wins: int = 0


class AntiFOMOManager:
    """
    FOMO Detection & Prevention System
    
    Prevents emotional trading by checking:
    - Setup completeness
    - Price movement (chasing)
    - Entry timing
    - Emotional state
    """
    
    def __init__(self):
        # Thresholds
        self.PRICE_CHASE_THRESHOLD = 3.0  # %3 from zone
        self.MIN_TIME_BETWEEN_TRADES = 15  # minutes
        self.ATR_SPIKE_THRESHOLD = 100  # %100 increase (doubled)
        self.LOW_PATIENCE_THRESHOLD = 0.3
        self.FOMO_SCORE_THRESHOLD = 50  # Block if >= 50
        
        # Scoring weights
        self.INCOMPLETE_SETUP_SCORE = 50
        self.PRICE_CHASING_SCORE = 60
        self.RAPID_TRADING_SCORE = 40
        self.LOW_PATIENCE_SCORE = 30
        self.VOLATILITY_SPIKE_SCORE = 50
    
    def detect_fomo(
        self, 
        setup: SetupData, 
        bot_state: BotState
    ) -> Dict:
        """
        Main FOMO detection function
        
        Returns:
            Dict with:
            - is_fomo: bool
            - score: int (0-200+)
            - signals: List[str]
            - reason: str
            - action: str
        """
        
        fomo_signals: List[str] = []
        fomo_score = 0
        
        # ════════════════════════════════════
        # CHECK 1: Setup Completeness
        # ════════════════════════════════════
        if not self._is_setup_complete(setup):
            fomo_signals.append('setup_incomplete')
            fomo_score += self.INCOMPLETE_SETUP_SCORE
        
        # ════════════════════════════════════
        # CHECK 2: Price Chasing
        # ════════════════════════════════════
        if self._is_price_chasing(setup):
            fomo_signals.append('chasing_price')
            fomo_score += self.PRICE_CHASING_SCORE
        
        # ════════════════════════════════════
        # CHECK 3: Rapid Trading
        # ════════════════════════════════════
        if self._is_rapid_trading(bot_state):
            fomo_signals.append('rapid_trading')
            fomo_score += self.RAPID_TRADING_SCORE
        
        # ════════════════════════════════════
        # CHECK 4: Low Patience
        # ════════════════════════════════════
        if bot_state.patience < self.LOW_PATIENCE_THRESHOLD:
            fomo_signals.append('low_patience')
            fomo_score += self.LOW_PATIENCE_SCORE
        
        # ════════════════════════════════════
        # CHECK 5: Volatility Spike
        # ════════════════════════════════════
        if self._is_volatility_spike(setup):
            fomo_signals.append('volatility_spike')
            fomo_score += self.VOLATILITY_SPIKE_SCORE
        
        # ════════════════════════════════════
        # DECISION
        # ════════════════════════════════════
        is_fomo = fomo_score >= self.FOMO_SCORE_THRESHOLD
        
        if is_fomo:
            reason = f"FOMO detected: {', '.join(fomo_signals)}"
            action = "BLOCK TRADE"
        else:
            reason = "No FOMO detected"
            action = "ALLOW"
        
        return {
            'is_fomo': is_fomo,
            'score': fomo_score,
            'signals': fomo_signals,
            'reason': reason,
            'action': action,
            'details': self._generate_details(setup, bot_state, fomo_signals)
        }
    
    def _is_setup_complete(self, setup: SetupData) -> bool:
        """Check if all PA conditions are met"""
        required = [
            setup.zone is not None,
            setup.choch is not None,
            setup.fib_retest is not None
        ]
        return all(required)
    
    def _is_price_chasing(self, setup: SetupData) -> bool:
        """Check if price moved too far from zone"""
        if setup.zone_price == 0 or setup.current_price == 0:
            return False
        
        distance_percent = abs(
            setup.current_price - setup.zone_price
        ) / setup.zone_price * 100
        
        return distance_percent > self.PRICE_CHASE_THRESHOLD
    
    def _is_rapid_trading(self, bot_state: BotState) -> bool:
        """Check if trading too fast"""
        return bot_state.minutes_since_last_trade < self.MIN_TIME_BETWEEN_TRADES
    
    def _is_volatility_spike(self, setup: SetupData) -> bool:
        """Check if ATR suddenly increased"""
        return setup.atr_change_percent > self.ATR_SPIKE_THRESHOLD
    
    def _generate_details(
        self, 
        setup: SetupData, 
        bot_state: BotState,
        signals: List[str]
    ) -> Dict:
        """Generate detailed explanation"""
        details = {}
        
        if 'setup_incomplete' in signals:
            missing = []
            if setup.zone is None:
                missing.append('zone')
            if setup.choch is None:
                missing.append('choch')
            if setup.fib_retest is None:
                missing.append('fib_retest')
            details['missing_conditions'] = missing
        
        if 'chasing_price' in signals:
            distance = abs(setup.current_price - setup.zone_price)
            distance_pct = distance / setup.zone_price * 100
            details['price_distance'] = {
                'absolute': distance,
                'percent': f"{distance_pct:.2f}%",
                'threshold': f"{self.PRICE_CHASE_THRESHOLD}%"
            }
        
        if 'rapid_trading' in signals:
            details['time_since_last'] = {
                'minutes': bot_state.minutes_since_last_trade,
                'required': self.MIN_TIME_BETWEEN_TRADES
            }
        
        if 'low_patience' in signals:
            details['patience'] = {
                'current': f"{bot_state.patience:.2f}",
                'threshold': f"{self.LOW_PATIENCE_THRESHOLD:.2f}"
            }
        
        if 'volatility_spike' in signals:
            details['atr_change'] = {
                'percent': f"{setup.atr_change_percent:.1f}%",
                'threshold': f"{self.ATR_SPIKE_THRESHOLD}%"
            }
        
        return details
    
    def validate_entry_timing(
        self, 
        setup: SetupData
    ) -> Dict:
        """
        Validate entry timing (separate from FOMO)
        
        Checks:
        - Setup not too old
        - Price didn't run away
        - Fibonacci retest occurred
        """
        
        issues = []
        
        # Check setup age
        if setup.candles_since_setup > 5:
            issues.append('setup_too_old')
        
        # Check if fib retest happened
        if setup.fib_retest is None:
            issues.append('no_fib_retest')
        
        # Check price movement
        if setup.setup_age_minutes > 60:  # 1 hour old
            issues.append('stale_setup')
        
        is_valid = len(issues) == 0
        
        return {
            'valid': is_valid,
            'issues': issues,
            'recommendation': 'ALLOW' if is_valid else 'SKIP',
            'reason': ', '.join(issues) if issues else 'Timing OK'
        }


# ════════════════════════════════════════
# USAGE EXAMPLES
# ════════════════════════════════════════

def example_scenarios():
    """Example FOMO detection scenarios"""
    
    manager = AntiFOMOManager()
    
    print("=" * 60)
    print("ANTI-FOMO DETECTION EXAMPLES")
    print("=" * 60)
    print()
    
    # ════════════════════════════════════════
    # SCENARIO 1: Classic FOMO (BLOCKED)
    # ════════════════════════════════════════
    print("SCENARIO 1: Classic FOMO (Price Chasing)")
    print("-" * 60)
    
    fomo_setup = SetupData(
        zone={'price': 50000},
        choch=None,  # Missing!
        fib_retest=None,  # Missing!
        zone_price=50000,
        current_price=51700,  # 3.4% away
        setup_score=72,
        zone_quality=7,
        atr_percent=5.5
    )
    
    fomo_bot_state = BotState(
        confidence=0.6,
        stress=0.3,
        patience=0.2,  # Low!
        minutes_since_last_trade=5  # Too fast!
    )
    
    result = manager.detect_fomo(fomo_setup, fomo_bot_state)
    print(f"FOMO Detected: {result['is_fomo']}")
    print(f"Score: {result['score']}")
    print(f"Signals: {result['signals']}")
    print(f"Action: {result['action']}")
    print(f"Reason: {result['reason']}")
    print()
    
    # ════════════════════════════════════════
    # SCENARIO 2: Patient Entry (ALLOWED)
    # ════════════════════════════════════════
    print("SCENARIO 2: Patient Entry (All Good)")
    print("-" * 60)
    
    good_setup = SetupData(
        zone={'price': 50000},
        choch={'strength': 0.75},
        fib_retest={'level': 0.705},
        zone_price=50000,
        current_price=50150,  # 0.3% away (good!)
        setup_score=85,
        zone_quality=8,
        atr_percent=5.2,
        atr_change_percent=10  # Normal
    )
    
    good_bot_state = BotState(
        confidence=0.75,
        stress=0.25,
        patience=0.8,  # High!
        minutes_since_last_trade=45  # Good wait
    )
    
    result = manager.detect_fomo(good_setup, good_bot_state)
    print(f"FOMO Detected: {result['is_fomo']}")
    print(f"Score: {result['score']}")
    print(f"Signals: {result['signals']}")
    print(f"Action: {result['action']}")
    print(f"Reason: {result['reason']}")
    print()
    
    # ════════════════════════════════════════
    # SCENARIO 3: Volatility Spike (BLOCKED)
    # ════════════════════════════════════════
    print("SCENARIO 3: Volatility Spike (News Event)")
    print("-" * 60)
    
    volatile_setup = SetupData(
        zone={'price': 50000},
        choch={'strength': 0.82},
        fib_retest={'level': 0.705},
        zone_price=50000,
        current_price=50100,
        setup_score=78,
        zone_quality=7,
        atr_percent=12.0,  # High!
        atr_change_percent=150  # ATR 2.5x (spike!)
    )
    
    normal_bot_state = BotState(
        confidence=0.7,
        stress=0.2,
        patience=0.75,
        minutes_since_last_trade=30
    )
    
    result = manager.detect_fomo(volatile_setup, normal_bot_state)
    print(f"FOMO Detected: {result['is_fomo']}")
    print(f"Score: {result['score']}")
    print(f"Signals: {result['signals']}")
    print(f"Action: {result['action']}")
    print(f"Reason: {result['reason']}")
    if 'volatility_spike' in result['signals']:
        print(f"ATR Details: {result['details'].get('atr_change')}")
    print()
    
    # ════════════════════════════════════════
    # SCENARIO 4: Entry Timing Validation
    # ════════════════════════════════════════
    print("SCENARIO 4: Entry Timing Check")
    print("-" * 60)
    
    old_setup = SetupData(
        zone={'price': 50000},
        choch={'strength': 0.65},
        fib_retest={'level': 0.618},
        candles_since_setup=7,  # Too old!
        setup_age_minutes=85,  # 1h 25min
    )
    
    timing_result = manager.validate_entry_timing(old_setup)
    print(f"Valid Timing: {timing_result['valid']}")
    print(f"Issues: {timing_result['issues']}")
    print(f"Recommendation: {timing_result['recommendation']}")
    print()
    
    print("=" * 60)


if __name__ == "__main__":
    example_scenarios()
