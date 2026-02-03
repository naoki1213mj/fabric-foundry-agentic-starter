"""
Product Comparison Tools

Provides tools for product comparison, price-performance analysis,
alternative suggestions, and bundle discount calculations.
"""

import json
from typing import Any


class ProductComparisonTools:
    """Product comparison and recommendation tools."""

    def get_tool_definitions(self) -> list[dict]:
        """Return MCP tool definitions for product comparison tools."""
        return [
            {
                "name": "compare_products",
                "description": "2つの製品を比較して比較表を生成します。価格、スペック、特徴の差分を表示。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_a": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "price": {"type": "number"},
                                "specs": {"type": "object"},
                            },
                            "description": "製品Aの情報（名前、価格、スペック）",
                        },
                        "product_b": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "price": {"type": "number"},
                                "specs": {"type": "object"},
                            },
                            "description": "製品Bの情報（名前、価格、スペック）",
                        },
                    },
                    "required": ["product_a", "product_b"],
                },
            },
            {
                "name": "calculate_price_performance",
                "description": "価格性能比（コストパフォーマンス）を計算します。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "price": {"type": "number", "description": "製品価格"},
                        "performance_score": {
                            "type": "number",
                            "description": "性能スコア（1-100）",
                        },
                        "product_name": {"type": "string", "description": "製品名（オプション）"},
                    },
                    "required": ["price", "performance_score"],
                },
            },
            {
                "name": "suggest_alternatives",
                "description": "基準製品に対する代替製品をスコアリングして提案します。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "base_product": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "price": {"type": "number"},
                                "category": {"type": "string"},
                                "features": {"type": "array", "items": {"type": "string"}},
                            },
                            "description": "基準製品の情報",
                        },
                        "candidates": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "price": {"type": "number"},
                                    "category": {"type": "string"},
                                    "features": {"type": "array", "items": {"type": "string"}},
                                },
                            },
                            "description": "代替候補製品のリスト",
                        },
                    },
                    "required": ["base_product", "candidates"],
                },
            },
            {
                "name": "calculate_bundle_discount",
                "description": "バンドル購入時の割引を計算します。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "products": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "price": {"type": "number"},
                                    "quantity": {"type": "integer"},
                                },
                            },
                            "description": "購入製品リスト（名前、単価、数量）",
                        },
                        "discount_rules": {
                            "type": "object",
                            "properties": {
                                "bundle_discount_percent": {"type": "number"},
                                "quantity_discount_threshold": {"type": "integer"},
                                "quantity_discount_percent": {"type": "number"},
                            },
                            "description": "割引ルール（バンドル割引率、数量割引閾値、数量割引率）",
                        },
                    },
                    "required": ["products"],
                },
            },
        ]

    def compare_products(self, product_a: dict[str, Any], product_b: dict[str, Any]) -> str:
        """
        Compare two products and generate comparison table.

        Args:
            product_a: Product A information
            product_b: Product B information

        Returns:
            JSON string with comparison result
        """
        name_a = product_a.get("name", "製品A")
        name_b = product_b.get("name", "製品B")
        price_a = product_a.get("price", 0)
        price_b = product_b.get("price", 0)
        specs_a = product_a.get("specs", {})
        specs_b = product_b.get("specs", {})

        # Price comparison
        price_diff = price_a - price_b
        price_diff_percent = (price_diff / price_b * 100) if price_b > 0 else 0
        cheaper = name_b if price_diff > 0 else (name_a if price_diff < 0 else "同価格")

        # Spec comparison
        all_specs = set(specs_a.keys()) | set(specs_b.keys())
        spec_comparison = []
        a_advantages = []
        b_advantages = []

        for spec in sorted(all_specs):
            val_a = specs_a.get(spec, "-")
            val_b = specs_b.get(spec, "-")

            # Try numeric comparison
            try:
                num_a = float(val_a) if val_a != "-" else None
                num_b = float(val_b) if val_b != "-" else None
                if num_a is not None and num_b is not None:
                    if num_a > num_b:
                        winner = name_a
                        a_advantages.append(spec)
                    elif num_b > num_a:
                        winner = name_b
                        b_advantages.append(spec)
                    else:
                        winner = "同等"
                else:
                    winner = "-"
            except (ValueError, TypeError):
                winner = "-"

            spec_comparison.append({"spec": spec, name_a: val_a, name_b: val_b, "winner": winner})

        result = {
            "comparison_table": spec_comparison,
            "price_comparison": {
                name_a: price_a,
                name_b: price_b,
                "difference": abs(price_diff),
                "difference_percent": round(abs(price_diff_percent), 1),
                "cheaper": cheaper,
            },
            "advantages": {name_a: a_advantages, name_b: b_advantages},
            "summary": {
                "products_compared": [name_a, name_b],
                "total_specs_compared": len(spec_comparison),
                "recommendation": f"{cheaper}がコスト面で有利" if price_diff != 0 else "価格は同等",
            },
            "analysis": f"製品比較: {name_a} vs {name_b} - 価格差 ¥{abs(price_diff):,.0f}（{cheaper}が安い）",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def calculate_price_performance(
        self, price: float, performance_score: float, product_name: str = None
    ) -> str:
        """
        Calculate price-performance ratio.

        Args:
            price: Product price
            performance_score: Performance score (1-100)
            product_name: Product name (optional)

        Returns:
            JSON string with price-performance analysis
        """
        if price <= 0:
            return json.dumps(
                {"error": "価格は正の値である必要があります", "price": price}, ensure_ascii=False
            )

        if not (1 <= performance_score <= 100):
            return json.dumps(
                {
                    "error": "性能スコアは1-100の範囲である必要があります",
                    "performance_score": performance_score,
                },
                ensure_ascii=False,
            )

        # Calculate cost per performance point
        cost_per_point = price / performance_score

        # Calculate value score (inverse - higher is better)
        # Normalized to 100 scale assuming ¥10,000 per point is baseline
        baseline_cost_per_point = 10000
        value_score = (baseline_cost_per_point / cost_per_point) * 50
        value_score = min(100, max(1, value_score))  # Clamp to 1-100

        # Rating based on value score
        if value_score >= 80:
            rating = "★★★★★ 非常にお買い得"
        elif value_score >= 60:
            rating = "★★★★☆ お買い得"
        elif value_score >= 40:
            rating = "★★★☆☆ 適正価格"
        elif value_score >= 20:
            rating = "★★☆☆☆ やや割高"
        else:
            rating = "★☆☆☆☆ 割高"

        result = {
            "product_name": product_name or "対象製品",
            "price": price,
            "performance_score": performance_score,
            "cost_per_point": round(cost_per_point, 2),
            "value_score": round(value_score, 1),
            "rating": rating,
            "analysis": f"コスパ分析: {product_name or '対象製品'} - 価格 ¥{price:,.0f} / 性能 {performance_score}点 = {rating}",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def suggest_alternatives(
        self, base_product: dict[str, Any], candidates: list[dict[str, Any]]
    ) -> str:
        """
        Suggest alternative products with similarity scoring.

        Args:
            base_product: Base product for comparison
            candidates: List of candidate products

        Returns:
            JSON string with ranked alternatives
        """
        if not candidates:
            return json.dumps({"error": "代替候補製品のリストが空です"}, ensure_ascii=False)

        base_name = base_product.get("name", "基準製品")
        base_price = base_product.get("price", 0)
        base_category = base_product.get("category", "")
        base_features = set(base_product.get("features", []))

        scored_candidates = []

        for candidate in candidates:
            cand_name = candidate.get("name", "候補製品")
            cand_price = candidate.get("price", 0)
            cand_category = candidate.get("category", "")
            cand_features = set(candidate.get("features", []))

            # Calculate similarity score
            score = 0

            # Category match (30 points)
            if cand_category == base_category:
                score += 30

            # Price similarity (30 points) - within 20% is full score
            if base_price > 0 and cand_price > 0:
                price_ratio = cand_price / base_price
                if 0.8 <= price_ratio <= 1.2:
                    score += 30
                elif 0.6 <= price_ratio <= 1.4:
                    score += 20
                elif 0.4 <= price_ratio <= 1.6:
                    score += 10

            # Feature overlap (40 points)
            if base_features and cand_features:
                overlap = len(base_features & cand_features)
                total = len(base_features | cand_features)
                if total > 0:
                    score += int((overlap / total) * 40)

            price_diff = cand_price - base_price
            price_indicator = "↑" if price_diff > 0 else ("↓" if price_diff < 0 else "=")

            scored_candidates.append(
                {
                    "name": cand_name,
                    "price": cand_price,
                    "price_vs_base": f"{price_indicator} ¥{abs(price_diff):,.0f}",
                    "category": cand_category,
                    "similarity_score": score,
                    "matching_features": list(base_features & cand_features)
                    if base_features
                    else [],
                }
            )

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)

        top_alternative = scored_candidates[0] if scored_candidates else None

        result = {
            "base_product": base_name,
            "alternatives": scored_candidates,
            "top_recommendation": top_alternative,
            "analysis": f"代替製品提案: {base_name}の代替として{top_alternative['name']}（類似度{top_alternative['similarity_score']}点）を推奨"
            if top_alternative
            else "代替候補なし",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def calculate_bundle_discount(
        self, products: list[dict[str, Any]], discount_rules: dict[str, Any] = None
    ) -> str:
        """
        Calculate bundle discount.

        Args:
            products: List of products with name, price, quantity
            discount_rules: Discount rules (optional)

        Returns:
            JSON string with discount calculation
        """
        if not products:
            return json.dumps({"error": "製品リストが空です"}, ensure_ascii=False)

        # Default discount rules
        rules = discount_rules or {
            "bundle_discount_percent": 5,  # 5% off for 2+ different products
            "quantity_discount_threshold": 3,  # 3+ same item
            "quantity_discount_percent": 10,  # 10% off for quantity
        }

        bundle_discount = rules.get("bundle_discount_percent", 5) / 100
        qty_threshold = rules.get("quantity_discount_threshold", 3)
        qty_discount = rules.get("quantity_discount_percent", 10) / 100

        line_items = []
        subtotal = 0

        for product in products:
            name = product.get("name", "製品")
            price = product.get("price", 0)
            quantity = product.get("quantity", 1)

            line_total = price * quantity
            subtotal += line_total

            # Check quantity discount
            item_discount = 0
            if quantity >= qty_threshold:
                item_discount = line_total * qty_discount

            line_items.append(
                {
                    "name": name,
                    "unit_price": price,
                    "quantity": quantity,
                    "line_total": line_total,
                    "quantity_discount": round(item_discount, 2),
                }
            )

        # Calculate bundle discount (if 2+ different products)
        total_quantity_discount = sum(item["quantity_discount"] for item in line_items)
        bundle_discount_amount = 0
        if len(products) >= 2:
            bundle_discount_amount = (subtotal - total_quantity_discount) * bundle_discount

        total_discount = total_quantity_discount + bundle_discount_amount
        final_total = subtotal - total_discount

        result = {
            "line_items": line_items,
            "subtotal": round(subtotal, 2),
            "discounts": {
                "quantity_discount": round(total_quantity_discount, 2),
                "bundle_discount": round(bundle_discount_amount, 2),
                "total_discount": round(total_discount, 2),
                "discount_percent": round(
                    (total_discount / subtotal * 100) if subtotal > 0 else 0, 1
                ),
            },
            "final_total": round(final_total, 2),
            "savings": round(total_discount, 2),
            "analysis": f"バンドル割引: 小計 ¥{subtotal:,.0f} - 割引 ¥{total_discount:,.0f} = 最終価格 ¥{final_total:,.0f}（{(total_discount / subtotal * 100) if subtotal > 0 else 0:.1f}% OFF）",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)
