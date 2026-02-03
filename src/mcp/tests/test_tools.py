"""
Tests for MCP Server Tools

Unit tests for sales analysis, product comparison, customer segmentation,
and inventory analysis tools.
"""

import json

import pytest
from tools.customer_segment import CustomerSegmentTools
from tools.inventory_analysis import InventoryAnalysisTools
from tools.product_comparison import ProductComparisonTools
from tools.sales_analysis import SalesAnalysisTools


class TestSalesAnalysisTools:
    """Tests for SalesAnalysisTools."""

    @pytest.fixture
    def tools(self):
        """Create SalesAnalysisTools instance."""
        return SalesAnalysisTools()

    def test_get_tool_definitions_returns_list(self, tools):
        """Tool definitions should return a list of 5 tools."""
        definitions = tools.get_tool_definitions()
        assert isinstance(definitions, list)
        assert len(definitions) == 5

    def test_calculate_yoy_growth_positive(self, tools):
        """YoY growth should calculate positive growth correctly."""
        result = json.loads(tools.calculate_yoy_growth(120000, 100000))
        assert result["growth_rate_percent"] == 20.0
        assert result["change_amount"] == 20000
        assert result["trend"] == "増加"

    def test_calculate_yoy_growth_negative(self, tools):
        """YoY growth should calculate negative growth correctly."""
        result = json.loads(tools.calculate_yoy_growth(80000, 100000))
        assert result["growth_rate_percent"] == -20.0
        assert result["change_amount"] == -20000
        assert result["trend"] == "減少"

    def test_calculate_yoy_growth_zero_previous(self, tools):
        """YoY growth should handle zero previous value."""
        result = json.loads(tools.calculate_yoy_growth(100000, 0))
        assert result["growth_rate_percent"] is None  # Infinity
        assert "∞" in result["growth_rate_display"]

    def test_calculate_mom_growth(self, tools):
        """MoM growth calculation should work correctly."""
        result = json.loads(tools.calculate_mom_growth(110000, 100000))
        assert result["growth_rate_percent"] == 10.0
        assert result["trend"] == "増加"

    def test_calculate_moving_average(self, tools):
        """Moving average should be calculated correctly."""
        values = [100, 200, 300, 400, 500]
        result = json.loads(tools.calculate_moving_average(values, period=3))
        # MA: (100+200+300)/3=200, (200+300+400)/3=300, (300+400+500)/3=400
        assert result["moving_averages"] == [200.0, 300.0, 400.0]
        assert result["latest_value"] == 400.0
        assert result["trend"] == "上昇傾向"

    def test_calculate_moving_average_insufficient_data(self, tools):
        """Moving average should handle insufficient data."""
        values = [100, 200]
        result = json.loads(tools.calculate_moving_average(values, period=5))
        assert "error" in result

    def test_calculate_abc_analysis(self, tools):
        """ABC analysis should classify items correctly."""
        items = [
            {"name": "Product A", "value": 70000},
            {"name": "Product B", "value": 20000},
            {"name": "Product C", "value": 10000},
        ]
        result = json.loads(tools.calculate_abc_analysis(items))
        assert result["summary"]["A_count"] >= 1
        assert "Product A" in result["summary"]["A_items"]

    def test_calculate_abc_analysis_empty(self, tools):
        """ABC analysis should handle empty items."""
        result = json.loads(tools.calculate_abc_analysis([]))
        assert "error" in result

    def test_calculate_sales_forecast(self, tools):
        """Sales forecast should predict future values."""
        # Linear growth: 100, 200, 300, 400 -> next should be ~500
        values = [100, 200, 300, 400]
        result = json.loads(tools.calculate_sales_forecast(values, periods_ahead=1))
        assert len(result["forecasts"]) == 1
        assert result["forecasts"][0]["forecast_value"] == 500.0  # Linear extrapolation
        assert result["model"]["trend"] == "上昇"

    def test_calculate_sales_forecast_insufficient_data(self, tools):
        """Sales forecast should require at least 2 data points."""
        result = json.loads(tools.calculate_sales_forecast([100]))
        assert "error" in result


class TestProductComparisonTools:
    """Tests for ProductComparisonTools."""

    @pytest.fixture
    def tools(self):
        """Create ProductComparisonTools instance."""
        return ProductComparisonTools()

    def test_get_tool_definitions_returns_list(self, tools):
        """Tool definitions should return a list of 4 tools."""
        definitions = tools.get_tool_definitions()
        assert isinstance(definitions, list)
        assert len(definitions) == 4

    def test_compare_products(self, tools):
        """Product comparison should compare two products."""
        product_a = {
            "name": "iPhone",
            "price": 150000,
            "specs": {"storage": 256, "ram": 6}
        }
        product_b = {
            "name": "Galaxy",
            "price": 120000,
            "specs": {"storage": 256, "ram": 8}
        }
        result = json.loads(tools.compare_products(product_a, product_b))
        assert "comparison_table" in result
        assert result["price_comparison"]["cheaper"] == "Galaxy"
        assert result["price_comparison"]["difference"] == 30000

    def test_calculate_price_performance(self, tools):
        """Price performance should calculate value score."""
        result = json.loads(tools.calculate_price_performance(
            price=100000,
            performance_score=80,
            product_name="Test Product"
        ))
        assert "value_score" in result
        assert "rating" in result
        assert result["product_name"] == "Test Product"

    def test_calculate_price_performance_invalid_price(self, tools):
        """Price performance should handle invalid price."""
        result = json.loads(tools.calculate_price_performance(price=0, performance_score=80))
        assert "error" in result

    def test_calculate_price_performance_invalid_score(self, tools):
        """Price performance should handle invalid score."""
        result = json.loads(tools.calculate_price_performance(price=100000, performance_score=150))
        assert "error" in result

    def test_suggest_alternatives(self, tools):
        """Alternative suggestion should score and rank candidates."""
        base = {
            "name": "Base Product",
            "price": 10000,
            "category": "Electronics",
            "features": ["wifi", "bluetooth"]
        }
        candidates = [
            {"name": "Alt 1", "price": 9000, "category": "Electronics", "features": ["wifi"]},
            {"name": "Alt 2", "price": 15000, "category": "Clothing", "features": ["cotton"]},
        ]
        result = json.loads(tools.suggest_alternatives(base, candidates))
        assert len(result["alternatives"]) == 2
        assert result["top_recommendation"]["name"] == "Alt 1"

    def test_suggest_alternatives_empty(self, tools):
        """Alternative suggestion should handle empty candidates."""
        result = json.loads(tools.suggest_alternatives({"name": "Base"}, []))
        assert "error" in result

    def test_calculate_bundle_discount(self, tools):
        """Bundle discount should calculate total savings."""
        products = [
            {"name": "Item A", "price": 10000, "quantity": 2},
            {"name": "Item B", "price": 5000, "quantity": 1},
        ]
        result = json.loads(tools.calculate_bundle_discount(products))
        assert result["subtotal"] == 25000  # 10000*2 + 5000*1
        assert result["discounts"]["total_discount"] > 0
        assert result["final_total"] < result["subtotal"]


class TestCustomerSegmentTools:
    """Tests for CustomerSegmentTools."""

    @pytest.fixture
    def tools(self):
        """Create CustomerSegmentTools instance."""
        return CustomerSegmentTools()

    def test_get_tool_definitions_returns_list(self, tools):
        """Tool definitions should return a list of 4 tools."""
        definitions = tools.get_tool_definitions()
        assert isinstance(definitions, list)
        assert len(definitions) == 4

    def test_calculate_rfm_score_vip(self, tools):
        """RFM score should identify VIP customer."""
        # Recent purchase (3 days), high frequency (25), high monetary (600000)
        result = json.loads(tools.calculate_rfm_score(
            recency_days=3,
            frequency=25,
            monetary=600000
        ))
        assert result["rfm_scores"]["recency"] == 5
        assert result["rfm_scores"]["frequency"] == 5
        assert result["rfm_scores"]["monetary"] == 5
        assert result["score_label"] == "R5F5M5"

    def test_calculate_rfm_score_dormant(self, tools):
        """RFM score should identify dormant customer."""
        # Old purchase (200 days), low frequency (1), low monetary (30000)
        result = json.loads(tools.calculate_rfm_score(
            recency_days=200,
            frequency=1,
            monetary=30000
        ))
        assert result["rfm_scores"]["recency"] == 1
        assert result["rfm_scores"]["frequency"] == 1
        assert result["rfm_scores"]["monetary"] == 1

    def test_classify_customer_segment_vip(self, tools):
        """Segment classification should identify VIP."""
        result = json.loads(tools.classify_customer_segment(r_score=5, f_score=5, m_score=5))
        assert result["segment"]["name"] == "VIP顧客"
        assert result["segment"]["priority"] == 1

    def test_classify_customer_segment_at_risk(self, tools):
        """Segment classification should identify at-risk customer."""
        result = json.loads(tools.classify_customer_segment(r_score=1, f_score=2, m_score=4))
        assert result["segment"]["name"] == "離反リスク顧客"
        assert result["segment"]["priority"] == 1

    def test_calculate_clv(self, tools):
        """CLV should calculate customer lifetime value."""
        result = json.loads(tools.calculate_clv(
            average_purchase_value=50000,
            purchase_frequency_per_year=4,
            customer_lifespan_years=3
        ))
        assert result["calculations"]["annual_revenue"] == 200000
        assert result["calculations"]["simple_clv"] == 600000
        assert "tier" in result

    def test_recommend_next_action_vip(self, tools):
        """Next action should recommend appropriate action for VIP."""
        result = json.loads(tools.recommend_next_action(segment="VIP顧客"))
        assert result["recommendation"]["urgency"] == "通常"
        assert "専任担当者" in result["recommendation"]["channels"]

    def test_recommend_next_action_at_risk(self, tools):
        """Next action should recommend urgent action for at-risk."""
        result = json.loads(tools.recommend_next_action(
            segment="離反リスク顧客",
            last_purchase_days=100
        ))
        assert result["recommendation"]["urgency"] == "緊急"
        assert len(result["action_items"]) >= 2


class TestInventoryAnalysisTools:
    """Tests for InventoryAnalysisTools."""

    @pytest.fixture
    def tools(self):
        """Create InventoryAnalysisTools instance."""
        return InventoryAnalysisTools()

    def test_get_tool_definitions_returns_list(self, tools):
        """Tool definitions should return a list of 3 tools."""
        definitions = tools.get_tool_definitions()
        assert isinstance(definitions, list)
        assert len(definitions) == 3

    def test_calculate_inventory_turnover_high(self, tools):
        """Inventory turnover should calculate high turnover correctly."""
        # COGS 1,200,000, Avg inventory 100,000 -> 12x turnover
        result = json.loads(tools.calculate_inventory_turnover(
            cost_of_goods_sold=1200000,
            average_inventory=100000
        ))
        assert result["metrics"]["turnover_ratio"] == 12.0
        assert "非常に高回転" in result["rating"]

    def test_calculate_inventory_turnover_low(self, tools):
        """Inventory turnover should identify low turnover."""
        # COGS 100,000, Avg inventory 100,000 -> 1x turnover
        result = json.loads(tools.calculate_inventory_turnover(
            cost_of_goods_sold=100000,
            average_inventory=100000
        ))
        assert result["metrics"]["turnover_ratio"] == 1.0
        assert "低回転" in result["rating"]

    def test_calculate_inventory_turnover_invalid(self, tools):
        """Inventory turnover should handle invalid input."""
        result = json.loads(tools.calculate_inventory_turnover(
            cost_of_goods_sold=100000,
            average_inventory=0
        ))
        assert "error" in result

    def test_calculate_reorder_point(self, tools):
        """Reorder point should calculate correctly."""
        result = json.loads(tools.calculate_reorder_point(
            daily_demand=10,
            lead_time_days=7,
            safety_stock_days=3
        ))
        # Lead time demand = 10 * 7 = 70
        # Safety stock (fixed) = 10 * 3 = 30
        # Reorder point >= 70 + 30 = 100
        assert result["calculations"]["lead_time_demand"] == 70
        assert result["calculations"]["reorder_point"] >= 100

    def test_identify_slow_moving_inventory(self, tools):
        """Slow moving identification should classify items correctly."""
        items = [
            {"name": "Dead Item", "quantity": 100, "unit_cost": 1000, "days_in_stock": 200, "monthly_sales": 0},
            {"name": "Slow Item", "quantity": 50, "unit_cost": 500, "days_in_stock": 100, "monthly_sales": 2},
            {"name": "Healthy Item", "quantity": 30, "unit_cost": 200, "days_in_stock": 30, "monthly_sales": 20},
        ]
        result = json.loads(tools.identify_slow_moving_inventory(items))
        assert result["summary"]["dead_stock_count"] == 1
        assert result["summary"]["slow_moving_count"] == 1
        assert result["summary"]["healthy_count"] == 1
        assert "Dead Item" in result["summary"]["dead_stock_items"]

    def test_identify_slow_moving_inventory_empty(self, tools):
        """Slow moving identification should handle empty list."""
        result = json.loads(tools.identify_slow_moving_inventory([]))
        assert "error" in result
