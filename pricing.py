"""
Pricing configuration for Sysrai Platform
"""

PRICING = {
    "script_per_minute": 1.00,
    "video_per_minute": 3.00,
    "storyboard_flat": 10.00,
    "quality_multipliers": {
        "standard": 1.0,
        "premium": 1.5,
        "ultra": 2.0
    }
}

CREDIT_PACKAGES = {
    "small": {"credits": 50, "price": 19.99, "bonus": 0},
    "medium": {"credits": 150, "price": 49.99, "bonus": 10},
    "large": {"credits": 500, "price": 149.99, "bonus": 50},
    "mega": {"credits": 2000, "price": 499.99, "bonus": 300}
}

SUBSCRIPTION_TIERS = {
    "free": {
        "monthly_price": 0,
        "included_credits": 10,
        "price_per_minute": 5.00,
        "max_duration": 10
    },
    "starter": {
        "monthly_price": 29.99,
        "included_credits": 100,
        "price_per_minute": 3.00,
        "max_duration": 60
    },
    "pro": {
        "monthly_price": 99.99,
        "included_credits": 500,
        "price_per_minute": 2.50,
        "max_duration": 180
    },
    "enterprise": {
        "monthly_price": 499.99,
        "included_credits": 3000,
        "price_per_minute": 2.00,
        "max_duration": -1  # Unlimited
    }
}

def calculate_project_cost(duration_minutes: int, 
                          include_script: bool = True,
                          include_storyboard: bool = True,
                          quality: str = "standard") -> dict:
    """Calculate total project cost"""
    
    cost = {
        "video": duration_minutes * PRICING["video_per_minute"],
        "script": duration_minutes * PRICING["script_per_minute"] if include_script else 0,
        "storyboard": PRICING["storyboard_flat"] if include_storyboard else 0,
    }
    
    subtotal = sum(cost.values())
    quality_multiplier = PRICING["quality_multipliers"].get(quality, 1.0)
    total = subtotal * quality_multiplier
    
    return {
        "breakdown": cost,
        "subtotal": subtotal,
        "quality_multiplier": quality_multiplier,
        "total": total
    }