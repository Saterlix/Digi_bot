"""
Pricing engine for currency conversion and margin calculation.
Converts IDR prices from Digiflazz to UZS with configurable margins.
"""

import math
from typing import Union

from config import config


class PricingEngine:
    """
    Handles price conversion from IDR to UZS with margin calculations.
    
    Formula: final_price = (idr_price * exchange_rate * margin_percent) + margin_fixed
    All prices are rounded up to the nearest 100 UZS.
    """
    
    def __init__(
        self,
        exchange_rate: float = None,
        margin_percent: float = None,
        margin_fixed: int = None
    ):
        """
        Initialize the pricing engine.
        
        Args:
            exchange_rate: IDR to UZS exchange rate (default from config).
            margin_percent: Percentage margin multiplier (default from config).
            margin_fixed: Fixed margin to add in UZS (default from config).
        """
        self.exchange_rate = exchange_rate or config.EXCHANGE_RATE
        self.margin_percent = margin_percent or config.MARGIN_PERCENT
        self.margin_fixed = margin_fixed or config.MARGIN_FIXED
    
    def convert_idr_to_uzs(
        self,
        idr_price: Union[int, float],
        apply_margin: bool = True
    ) -> int:
        """
        Convert IDR price to UZS with margin.
        
        Args:
            idr_price: Price in Indonesian Rupiah.
            apply_margin: Whether to apply margin (default True).
        
        Returns:
            Price in Uzbek Som, rounded up to nearest 100.
        """
        if idr_price <= 0:
            return 0
        
        # Base conversion
        base_uzs = idr_price * self.exchange_rate
        
        if apply_margin:
            # Apply percentage margin
            with_percent_margin = base_uzs * self.margin_percent
            # Add fixed margin
            final_price = with_percent_margin + self.margin_fixed
        else:
            final_price = base_uzs
        
        # Round up to nearest 100
        return self._round_up_to_hundred(final_price)
    
    def _round_up_to_hundred(self, price: float) -> int:
        """
        Round a price up to the nearest 100.
        
        Args:
            price: The price to round.
        
        Returns:
            Price rounded up to nearest 100.
        """
        return int(math.ceil(price / 100) * 100)
    
    def calculate_profit(
        self,
        idr_price: Union[int, float]
    ) -> dict[str, int]:
        """
        Calculate the profit breakdown for a given IDR price.
        
        Args:
            idr_price: Original price in IDR.
        
        Returns:
            Dictionary with cost, selling price, and profit in UZS.
        """
        cost_uzs = self.convert_idr_to_uzs(idr_price, apply_margin=False)
        selling_uzs = self.convert_idr_to_uzs(idr_price, apply_margin=True)
        profit_uzs = selling_uzs - cost_uzs
        
        return {
            "cost_uzs": cost_uzs,
            "selling_uzs": selling_uzs,
            "profit_uzs": profit_uzs
        }
    
    def process_price_list(
        self,
        price_list: list[dict]
    ) -> list[dict]:
        """
        Process a list of products and add UZS prices.
        
        Args:
            price_list: List of product dictionaries from Digiflazz.
                       Each item should have a 'price' key with IDR value.
        
        Returns:
            List of products with added 'price_uzs' field.
        """
        processed = []
        
        for item in price_list:
            idr_price = item.get("price", 0)
            item_copy = item.copy()
            item_copy["price_uzs"] = self.convert_idr_to_uzs(idr_price)
            item_copy["price_idr"] = idr_price
            processed.append(item_copy)
        
        return processed


# Create a singleton instance
pricing_engine = PricingEngine()
