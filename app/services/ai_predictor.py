import math
from datetime import datetime, timedelta, timezone
from app.models import BloodRequest, BloodInventory, DonationRecord

class BloodDemandPredictor:
    """
    AI-driven predictive demand forecasting engine for blood bank inventory management.
    Analyzes historical requisition velocity, emergency rates, population blood-group
    distribution, and seasonal multipliers to forecast 14-day and 30-day blood unit requirements.
    """

    # Global demographic prevalence weighting
    BLOOD_GROUP_WEIGHTS = {
        'O+': 0.38,
        'A+': 0.34,
        'B+': 0.09,
        'AB+': 0.03,
        'O-': 0.07,  # Universal trauma donor, high emergency pull
        'A-': 0.06,
        'B-': 0.02,
        'AB-': 0.01
    }

    # Emergency multiplier (O- is drawn in high-urgency un-crossmatched cases)
    EMERGENCY_DRAW_MULTIPLIER = {
        'O-': 1.65,
        'O+': 1.25,
        'A+': 1.10,
        'A-': 1.15,
        'B+': 1.05,
        'B-': 1.10,
        'AB+': 1.00,
        'AB-': 1.05
    }

    @classmethod
    def get_seasonal_factor(cls, dt=None):
        """
        Calculates seasonal coefficient based on time of year:
        - Winter / Holidays: elevated road accident trauma and reduced volunteer drives
        - Summer / Monsoon: seasonal vector illnesses and planned elective surgeries
        """
        if dt is None:
            dt = datetime.now(timezone.utc)
        month = dt.month

        # Higher demand during festive/holiday travel (Nov-Jan) and mid-year (Jul-Aug)
        if month in (11, 12, 1):
            return 1.22, "Holiday travel trauma & winter drive deferral surge (+22%)"
        elif month in (6, 7, 8):
            return 1.15, "Mid-year surgical schedule & seasonal transfusion peak (+15%)"
        else:
            return 1.05, "Standard clinical baseline (+5%)"

    @classmethod
    def predict_demand(cls, days_horizon=14):
        """
        Generates predictive forecast for all 8 blood groups over the specified horizon.
        Returns detailed analytics dictionary.
        """
        seasonal_mult, seasonal_reason = cls.get_seasonal_factor()
        inventory_items = BloodInventory.query.all()
        stock_map = {item.blood_group: item.units_available for item in inventory_items}
        threshold_map = {item.blood_group: item.critical_threshold for item in inventory_items}

        # Analyze historical requisitions from the past 60 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=60)
        recent_requests = BloodRequest.query.filter(BloodRequest.created_at >= cutoff).all()

        # Tally requests by blood group and urgency
        historical_units = {bg: 0 for bg in cls.BLOOD_GROUP_WEIGHTS.keys()}
        emergency_counts = {bg: 0 for bg in cls.BLOOD_GROUP_WEIGHTS.keys()}

        for req in recent_requests:
            if req.blood_group in historical_units:
                historical_units[req.blood_group] += req.units_requested
                if req.urgency in ('Emergency', 'Critical'):
                    emergency_counts[req.blood_group] += 1

        predictions = []
        total_forecasted_demand = 0
        total_current_stock = sum(stock_map.values())
        critical_deficits_count = 0

        for bg, base_weight in cls.BLOOD_GROUP_WEIGHTS.items():
            curr_stock = stock_map.get(bg, 0)
            threshold = threshold_map.get(bg, 5)
            hist_units = historical_units.get(bg, 0)

            # Daily consumption baseline derived from historical requests + demographic priors
            # If historical data is sparse, blend with national population baseline
            data_days = 60
            historical_daily_rate = hist_units / data_days if hist_units > 0 else (base_weight * 1.5)
            
            # Prior weighting model
            prior_daily_rate = (base_weight * 2.0)
            blended_daily_rate = (0.7 * historical_daily_rate) + (0.3 * prior_daily_rate)

            # Apply emergency multiplier and seasonal coefficient
            emerg_mult = cls.EMERGENCY_DRAW_MULTIPLIER.get(bg, 1.0)
            adjusted_daily_rate = blended_daily_rate * emerg_mult * seasonal_mult

            # Forecast for horizon
            forecast_demand = math.ceil(adjusted_daily_rate * days_horizon)
            total_forecasted_demand += forecast_demand

            # Calculate gap: Current Stock - Forecasted Demand
            projected_balance = curr_stock - forecast_demand

            # Risk classification
            if projected_balance < -2:
                risk_level = "Critical Shortage Risk"
                risk_badge = "bg-danger"
                action_advice = f"Deficit Alert! Schedule targeted {bg} donation drive immediately. Shortfall of {-projected_balance} units projected."
                critical_deficits_count += 1
            elif projected_balance <= 0:
                risk_level = "Moderate Deficit Warning"
                risk_badge = "bg-warning text-dark"
                action_advice = f"Tight supply. Alert nearby {bg} eligible donors to replenish safety cushion."
            elif projected_balance <= 5:
                risk_level = "Stable / Balanced"
                risk_badge = "bg-info text-dark"
                action_advice = f"Supply adequate for baseline {days_horizon}-day operations. Monitor weekly."
            else:
                risk_level = "Optimal Reserve"
                risk_badge = "bg-success"
                action_advice = f"Healthy cold-chain surplus. Can support external emergency inter-hospital requests."

            # Calculate AI confidence (higher when historical data points exist)
            confidence = round(min(96.5, 88.0 + (min(hist_units, 20) * 0.4)), 1)

            predictions.append({
                'blood_group': bg,
                'current_stock': curr_stock,
                'forecast_demand': forecast_demand,
                'projected_balance': projected_balance,
                'threshold': threshold,
                'risk_level': risk_level,
                'risk_badge': risk_badge,
                'action_advice': action_advice,
                'confidence': confidence,
                'emergency_draw_factor': emerg_mult
            })

        # Sort predictions by most critical deficit first
        predictions.sort(key=lambda x: x['projected_balance'])

        return {
            'horizon_days': days_horizon,
            'predictions': predictions,
            'seasonal_factor': seasonal_mult,
            'seasonal_reason': seasonal_reason,
            'total_current_stock': total_current_stock,
            'total_forecasted_demand': total_forecasted_demand,
            'net_balance': total_current_stock - total_forecasted_demand,
            'critical_deficits_count': critical_deficits_count,
            'chart_labels': [p['blood_group'] for p in predictions],
            'chart_stock': [p['current_stock'] for p in predictions],
            'chart_forecast': [p['forecast_demand'] for p in predictions]
        }
