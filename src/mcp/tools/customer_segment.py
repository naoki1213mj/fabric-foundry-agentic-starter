"""
Customer Segmentation Tools

Provides tools for customer analysis including RFM scoring, customer segmentation,
Customer Lifetime Value (CLV) calculation, and next action recommendations.
"""

import json


class CustomerSegmentTools:
    """Customer segmentation and analysis tools."""

    def get_tool_definitions(self) -> list[dict]:
        """Return MCP tool definitions for customer segmentation tools."""
        return [
            {
                "name": "calculate_rfm_score",
                "description": "RFM分析（Recency, Frequency, Monetary）スコアを計算します。顧客の購買行動を3軸で評価。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "recency_days": {"type": "integer", "description": "最終購入からの日数"},
                        "frequency": {"type": "integer", "description": "購入回数（期間内）"},
                        "monetary": {"type": "number", "description": "累計購入金額"},
                        "customer_id": {"type": "string", "description": "顧客ID（オプション）"},
                    },
                    "required": ["recency_days", "frequency", "monetary"],
                },
            },
            {
                "name": "classify_customer_segment",
                "description": "RFMスコアに基づいて顧客をセグメント分類します（VIP、優良顧客、休眠顧客など）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "r_score": {"type": "integer", "description": "Recencyスコア（1-5）"},
                        "f_score": {"type": "integer", "description": "Frequencyスコア（1-5）"},
                        "m_score": {"type": "integer", "description": "Monetaryスコア（1-5）"},
                        "customer_id": {"type": "string", "description": "顧客ID（オプション）"},
                    },
                    "required": ["r_score", "f_score", "m_score"],
                },
            },
            {
                "name": "calculate_clv",
                "description": "顧客生涯価値（CLV: Customer Lifetime Value）を計算します。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "average_purchase_value": {"type": "number", "description": "平均購入単価"},
                        "purchase_frequency_per_year": {
                            "type": "number",
                            "description": "年間平均購入回数",
                        },
                        "customer_lifespan_years": {
                            "type": "number",
                            "description": "顧客継続年数（予測）",
                            "default": 3,
                        },
                        "profit_margin": {
                            "type": "number",
                            "description": "利益率（0-1）",
                            "default": 0.3,
                        },
                        "discount_rate": {
                            "type": "number",
                            "description": "割引率（NPV計算用）",
                            "default": 0.1,
                        },
                    },
                    "required": ["average_purchase_value", "purchase_frequency_per_year"],
                },
            },
            {
                "name": "recommend_next_action",
                "description": "顧客セグメントに基づいてNext Best Actionを提案します。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "segment": {"type": "string", "description": "顧客セグメント名"},
                        "rfm_scores": {
                            "type": "object",
                            "properties": {
                                "r": {"type": "integer"},
                                "f": {"type": "integer"},
                                "m": {"type": "integer"},
                            },
                            "description": "RFMスコア（オプション）",
                        },
                        "last_purchase_days": {
                            "type": "integer",
                            "description": "最終購入からの日数（オプション）",
                        },
                    },
                    "required": ["segment"],
                },
            },
        ]

    def calculate_rfm_score(
        self, recency_days: int, frequency: int, monetary: float, customer_id: str | None = None
    ) -> str:
        """
        Calculate RFM scores.

        Args:
            recency_days: Days since last purchase
            frequency: Number of purchases
            monetary: Total purchase amount
            customer_id: Customer ID (optional)

        Returns:
            JSON string with RFM scores
        """
        # Recency score (1-5): lower days = higher score
        if recency_days <= 7:
            r_score = 5
        elif recency_days <= 30:
            r_score = 4
        elif recency_days <= 90:
            r_score = 3
        elif recency_days <= 180:
            r_score = 2
        else:
            r_score = 1

        # Frequency score (1-5): higher frequency = higher score
        if frequency >= 20:
            f_score = 5
        elif frequency >= 10:
            f_score = 4
        elif frequency >= 5:
            f_score = 3
        elif frequency >= 2:
            f_score = 2
        else:
            f_score = 1

        # Monetary score (1-5): higher spending = higher score
        if monetary >= 500000:
            m_score = 5
        elif monetary >= 200000:
            m_score = 4
        elif monetary >= 100000:
            m_score = 3
        elif monetary >= 50000:
            m_score = 2
        else:
            m_score = 1

        total_score = r_score + f_score + m_score
        avg_score = total_score / 3

        result = {
            "customer_id": customer_id or "N/A",
            "input_data": {
                "recency_days": recency_days,
                "frequency": frequency,
                "monetary": monetary,
            },
            "rfm_scores": {
                "recency": r_score,
                "frequency": f_score,
                "monetary": m_score,
                "total": total_score,
                "average": round(avg_score, 2),
            },
            "score_label": f"R{r_score}F{f_score}M{m_score}",
            "analysis": f"RFM分析: R{r_score}F{f_score}M{m_score}（平均{avg_score:.1f}点）- {'優良顧客' if avg_score >= 4 else '一般顧客' if avg_score >= 2.5 else '要フォロー顧客'}",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def classify_customer_segment(
        self, r_score: int, f_score: int, m_score: int, customer_id: str | None = None
    ) -> str:
        """
        Classify customer into segments based on RFM scores.

        Args:
            r_score: Recency score (1-5)
            f_score: Frequency score (1-5)
            m_score: Monetary score (1-5)
            customer_id: Customer ID (optional)

        Returns:
            JSON string with segment classification
        """
        # Segment classification logic
        if r_score >= 4 and f_score >= 4 and m_score >= 4:
            segment = "VIP顧客"
            description = "最も価値の高い顧客。特別な待遇と優先対応が必要"
            priority = 1
            color = "gold"
        elif r_score >= 4 and f_score >= 3 and m_score >= 3:
            segment = "優良顧客"
            description = "高頻度で購入する上位顧客。ロイヤルティ維持が重要"
            priority = 2
            color = "green"
        elif r_score >= 3 and f_score >= 3:
            segment = "有望顧客"
            description = "成長可能性のある顧客。アップセル/クロスセルの機会"
            priority = 3
            color = "blue"
        elif r_score >= 4 and f_score <= 2:
            segment = "新規顧客"
            description = "最近購入を始めた顧客。エンゲージメント強化が必要"
            priority = 4
            color = "cyan"
        elif r_score <= 2 and f_score >= 3:
            segment = "休眠優良顧客"
            description = "以前は優良だったが最近購入がない。再活性化が必要"
            priority = 2
            color = "orange"
        elif r_score <= 2 and m_score >= 3:
            segment = "離反リスク顧客"
            description = "高額購入履歴があるが離反の兆候。緊急フォロー必要"
            priority = 1
            color = "red"
        elif r_score <= 2 and f_score <= 2 and m_score <= 2:
            segment = "休眠顧客"
            description = "長期間購入がない顧客。再活性化キャンペーンの対象"
            priority = 5
            color = "gray"
        else:
            segment = "一般顧客"
            description = "標準的な購買パターンの顧客"
            priority = 4
            color = "white"

        # Recommended actions based on segment
        actions = {
            "VIP顧客": ["専任担当者のアサイン", "プレミアム特典の提供", "先行販売への招待"],
            "優良顧客": ["ロイヤルティプログラム案内", "レビュー依頼", "紹介キャンペーン"],
            "有望顧客": ["関連商品のレコメンド", "セット割引の提案", "会員ランクアップ案内"],
            "新規顧客": ["ウェルカムメール", "チュートリアル案内", "初回購入特典"],
            "休眠優良顧客": ["パーソナライズドオファー", "復帰キャンペーン", "アンケート実施"],
            "離反リスク顧客": ["緊急フォローコール", "限定割引クーポン", "サービス改善ヒアリング"],
            "休眠顧客": ["再活性化メール", "大幅割引オファー", "新商品案内"],
            "一般顧客": ["定期メルマガ", "季節キャンペーン案内", "レビュー依頼"],
        }

        result = {
            "customer_id": customer_id or "N/A",
            "rfm_scores": {"recency": r_score, "frequency": f_score, "monetary": m_score},
            "segment": {
                "name": segment,
                "description": description,
                "priority": priority,
                "color": color,
            },
            "recommended_actions": actions.get(segment, []),
            "analysis": f"顧客セグメント: {segment}（優先度{priority}）- {description}",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def calculate_clv(
        self,
        average_purchase_value: float,
        purchase_frequency_per_year: float,
        customer_lifespan_years: float = 3,
        profit_margin: float = 0.3,
        discount_rate: float = 0.1,
    ) -> str:
        """
        Calculate Customer Lifetime Value.

        Args:
            average_purchase_value: Average purchase amount
            purchase_frequency_per_year: Purchases per year
            customer_lifespan_years: Expected customer lifespan
            profit_margin: Profit margin (0-1)
            discount_rate: Discount rate for NPV

        Returns:
            JSON string with CLV calculation
        """
        # Annual revenue
        annual_revenue = average_purchase_value * purchase_frequency_per_year

        # Simple CLV (without discounting)
        simple_clv = annual_revenue * customer_lifespan_years

        # CLV with profit margin
        clv_profit = simple_clv * profit_margin

        # NPV-based CLV (discounted)
        npv_clv = 0
        yearly_values = []
        for year in range(1, int(customer_lifespan_years) + 1):
            year_value = (annual_revenue * profit_margin) / ((1 + discount_rate) ** year)
            npv_clv += year_value
            yearly_values.append(
                {
                    "year": year,
                    "revenue": round(annual_revenue, 0),
                    "profit": round(annual_revenue * profit_margin, 0),
                    "npv": round(year_value, 0),
                }
            )

        # CLV tier
        if npv_clv >= 500000:
            tier = "Platinum"
            tier_description = "最上位顧客"
        elif npv_clv >= 200000:
            tier = "Gold"
            tier_description = "上位顧客"
        elif npv_clv >= 100000:
            tier = "Silver"
            tier_description = "標準顧客"
        else:
            tier = "Bronze"
            tier_description = "育成対象顧客"

        result = {
            "input_parameters": {
                "average_purchase_value": average_purchase_value,
                "purchase_frequency_per_year": purchase_frequency_per_year,
                "customer_lifespan_years": customer_lifespan_years,
                "profit_margin": profit_margin,
                "discount_rate": discount_rate,
            },
            "calculations": {
                "annual_revenue": round(annual_revenue, 0),
                "simple_clv": round(simple_clv, 0),
                "clv_with_margin": round(clv_profit, 0),
                "npv_clv": round(npv_clv, 0),
            },
            "yearly_breakdown": yearly_values,
            "tier": {"name": tier, "description": tier_description},
            "analysis": f"CLV分析: 顧客生涯価値 ¥{npv_clv:,.0f}（{tier}ランク）- 年間 ¥{annual_revenue:,.0f} × {customer_lifespan_years}年",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)

    def recommend_next_action(
        self,
        segment: str,
        rfm_scores: dict[str, int] | None = None,
        last_purchase_days: int | None = None,
    ) -> str:
        """
        Recommend next best action based on customer segment.

        Args:
            segment: Customer segment name
            rfm_scores: RFM scores (optional)
            last_purchase_days: Days since last purchase (optional)

        Returns:
            JSON string with action recommendations
        """
        # Action catalog by segment
        action_catalog = {
            "VIP顧客": {
                "primary_action": "パーソナライズドサービス提供",
                "channels": ["専任担当者", "電話", "限定イベント"],
                "offer_type": "プレミアム特典",
                "urgency": "通常",
                "message_tone": "感謝・特別感",
            },
            "優良顧客": {
                "primary_action": "ロイヤルティ強化施策",
                "channels": ["メール", "アプリ通知", "DM"],
                "offer_type": "ポイント還元・限定商品",
                "urgency": "通常",
                "message_tone": "感謝・インセンティブ",
            },
            "有望顧客": {
                "primary_action": "アップセル/クロスセル提案",
                "channels": ["メール", "Web", "アプリ"],
                "offer_type": "セット割引・関連商品",
                "urgency": "中",
                "message_tone": "おすすめ・お得感",
            },
            "新規顧客": {
                "primary_action": "オンボーディング完了",
                "channels": ["メール", "アプリ", "LINE"],
                "offer_type": "初回購入特典・チュートリアル",
                "urgency": "高",
                "message_tone": "歓迎・サポート",
            },
            "休眠優良顧客": {
                "primary_action": "再活性化キャンペーン",
                "channels": ["メール", "電話", "DM"],
                "offer_type": "復帰特典・限定割引",
                "urgency": "高",
                "message_tone": "お久しぶり・特別オファー",
            },
            "離反リスク顧客": {
                "primary_action": "緊急リテンション施策",
                "channels": ["電話", "メール", "訪問"],
                "offer_type": "大幅割引・サービス改善提案",
                "urgency": "緊急",
                "message_tone": "謝罪・改善約束",
            },
            "休眠顧客": {
                "primary_action": "休眠掘り起こし",
                "channels": ["メール", "郵送DM"],
                "offer_type": "大幅割引・新商品案内",
                "urgency": "低",
                "message_tone": "新着情報・お得感",
            },
            "一般顧客": {
                "primary_action": "定期エンゲージメント",
                "channels": ["メール", "SNS"],
                "offer_type": "季節キャンペーン",
                "urgency": "低",
                "message_tone": "情報提供",
            },
        }

        # Get action for segment (or default)
        action_info = action_catalog.get(segment, action_catalog["一般顧客"])

        # Adjust urgency based on last purchase days
        if last_purchase_days is not None:
            if last_purchase_days > 90 and segment not in ["休眠顧客", "離反リスク顧客"]:
                action_info = action_info.copy()
                action_info["urgency"] = "高"
                action_info["additional_note"] = f"注意: {last_purchase_days}日間購入なし"

        # Specific action items
        action_items = []
        if action_info["urgency"] == "緊急":
            action_items = [
                {"priority": 1, "action": "担当者による電話連絡", "deadline": "24時間以内"},
                {"priority": 2, "action": "特別オファー準備", "deadline": "48時間以内"},
                {"priority": 3, "action": "フォローアップメール送信", "deadline": "1週間以内"},
            ]
        elif action_info["urgency"] == "高":
            action_items = [
                {"priority": 1, "action": "パーソナライズドメール送信", "deadline": "3日以内"},
                {"priority": 2, "action": "クーポン/オファー発行", "deadline": "1週間以内"},
            ]
        else:
            action_items = [
                {
                    "priority": 1,
                    "action": f"{action_info['channels'][0]}でのアプローチ",
                    "deadline": "2週間以内",
                }
            ]

        result = {
            "segment": segment,
            "rfm_scores": rfm_scores,
            "last_purchase_days": last_purchase_days,
            "recommendation": {
                "primary_action": action_info["primary_action"],
                "channels": action_info["channels"],
                "offer_type": action_info["offer_type"],
                "urgency": action_info["urgency"],
                "message_tone": action_info["message_tone"],
            },
            "action_items": action_items,
            "analysis": f"次のアクション: {action_info['primary_action']}（{action_info['urgency']}）- {action_info['channels'][0]}経由で{action_info['offer_type']}を提案",
        }

        return json.dumps(result, ensure_ascii=False, indent=2)
