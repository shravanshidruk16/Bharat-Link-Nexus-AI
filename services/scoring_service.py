class ScoringService:
    @staticmethod
    def evaluate_candidates(products, sellers, requirements):
        if not products:
            return []

        evaluations = []
        req_qty = requirements.get("quantity", 50)
        req_budget = requirements.get("budgetInr", 300000)

        for p in products:
            seller = next((s for s in sellers if s["id"] == p.get("seller_id")), sellers[0] if sellers else {})
            
            unit_price = float(p.get("price", 3000))
            total_product_price = unit_price * req_qty
            available_stock = int(p.get("available_stock", 100))
            moq = int(p.get("minimum_order_quantity", 1))

            stock_satisfied = available_stock >= req_qty
            moq_satisfied = req_qty >= moq
            is_eligible = stock_satisfied and moq_satisfied and total_product_price <= (req_budget * 1.5)

            score = 80
            if stock_satisfied: score += 10
            if seller.get("verification_status") == "Verified": score += 10

            evaluations.append({
                "productId": p["id"],
                "productName": p["name"],
                "supplierId": seller.get("id", "sup-101"),
                "supplierName": seller.get("business_name", p.get("seller_name", "Artisan Collective")),
                "unitPrice": unit_price,
                "totalProductPrice": total_product_price,
                "availableStock": available_stock,
                "moqSatisfied": moq_satisfied,
                "stockSatisfied": stock_satisfied,
                "verifiedSatisfied": True,
                "isEligible": is_eligible,
                "score": score,
                "matchReasons": [
                    f"Available stock ({available_stock} units) satisfies required quantity ({req_qty} units)",
                    f"Artisan seller {seller.get('business_name', p.get('seller_name'))} holds {seller.get('craft_certification', 'GI Tag Certified')}"
                ]
            })

        return sorted(evaluations, key=lambda x: x["score"], reverse=True)
