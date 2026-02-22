/** @odoo-module */

import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PurchaseOrderPopup } from "./purchase_order_popup";


patch(ControlButtons.prototype, {
    async onClickCreatePurchaseOrder() {
        const notification = this.env.services.notification;
        const order = this.pos.get_order();
        if (!order) {
            return;
        }

        const orderlines = order.get_orderlines();
        const partner = order.get_partner();

        // Check for vendor - use default vendor from config or order partner
        let vendorId = this.pos.config.po_vendor_id ? this.pos.config.po_vendor_id[0] : false;

        if (!vendorId && partner) {
            vendorId = partner.id;
        }

        if (!vendorId) {
            notification.add(
                _t("Please select a customer/vendor or configure a default vendor in POS settings."),
                { type: "danger" }
            );
            return;
        }

        if (orderlines.length === 0) {
            notification.add(
                _t("Please add at least one product to create a purchase order."),
                { type: "warning" }
            );
            return;
        }

        // Prepare order lines data
        const posProductList = [];
        for (const line of orderlines) {
            const product = line.product || line.get_product();
            if (!product) {
                continue;
            }

            // Get UOM ID safely
            let uomId = false;
            if (product.uom_id) {
                uomId = Array.isArray(product.uom_id) ? product.uom_id[0] : product.uom_id.id || product.uom_id;
            }

            posProductList.push({
                product: {
                    id: product.id,
                    quantity: line.get_quantity(),
                    uom_id: uomId,
                    price: product.standard_price || product.lst_price || line.get_unit_price(),
                }
            });
        }

        const orderData = {
            vendorId: vendorId,
            lines: posProductList,
            poState: this.pos.config.po_state || 'draft',
            cashierId: this.pos.user.id,
            sessionId: this.pos.session.id,
        };

        // Show popup
        this.dialog.add(PurchaseOrderPopup, {
            orderData: orderData,
            onConfirm: async (popupData) => {
                await this.createPurchaseOrder(orderData, popupData, order);
            },
        });
    },

    async createPurchaseOrder(orderData, popupData, order) {
        const orm = this.env.services.orm;
        const notification = this.env.services.notification;

        try {
            const result = await orm.call(
                "purchase.order",
                "create_purchase_order_from_pos",
                [
                    orderData.vendorId,
                    orderData.lines,
                    orderData.cashierId,
                    orderData.poState,
                    orderData.sessionId,
                    popupData.payWithCash,
                    popupData.billReference,
                    popupData.receiptImage,
                ]
            );

            if (result) {
                // Show success notification
                let message = _t("Purchase Order %s created successfully!", result.po_name);

                if (popupData.payWithCash) {
                    if (result.payment_created) {
                        message += " " + _t("Payment recorded from POS cash.");
                        notification.add(message, { type: "success" });
                    } else {
                        // PO created but payment failed
                        notification.add(message, { type: "success" });
                        notification.add(
                            _t("Warning: Payment could not be recorded. Please check the Odoo log for details."),
                            { type: "warning" }
                        );
                    }
                } else {
                    notification.add(message, { type: "success" });
                }

                // Clear the order after creating PO
                const linesToRemove = [...order.get_orderlines()];
                for (const line of linesToRemove) {
                    order.removeOrderline(line);
                }

                // Clear partner
                order.set_partner(false);
            }
        } catch (error) {
            console.error("PO Creation Error:", error);
            notification.add(
                _t("Failed to create Purchase Order: ") + (error.message || String(error)),
                { type: "danger" }
            );
        }
    }
});
