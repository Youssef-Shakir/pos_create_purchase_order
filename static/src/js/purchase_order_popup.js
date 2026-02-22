/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";


export class PurchaseOrderPopup extends Component {
    static template = "pos_create_purchase_order.PurchaseOrderPopup";
    static components = { Dialog };
    static props = {
        close: Function,
        orderData: Object,
        onConfirm: Function,
    };

    setup() {
        this.pos = usePos();
        this.state = useState({
            payWithCash: false,
            billReference: "",
            receiptImage: null,
            receiptImagePreview: null,
        });
    }

    get totalAmount() {
        let total = 0;
        for (const line of this.props.orderData.lines) {
            total += line.product.quantity * line.product.price;
        }
        return total.toFixed(2);
    }

    onPayWithCashChange(ev) {
        this.state.payWithCash = ev.target.checked;
    }

    onBillReferenceChange(ev) {
        this.state.billReference = ev.target.value;
    }

    async onImageCapture() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            // For simplicity, we'll use file input instead of camera capture
            // Camera capture would require a more complex implementation
            this.fileInput.click();
        } catch (error) {
            // Fallback to file input
            this.fileInput.click();
        }
    }

    onImageSelect(ev) {
        const file = ev.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.state.receiptImage = e.target.result;
                this.state.receiptImagePreview = e.target.result;
            };
            reader.readAsDataURL(file);
        }
    }

    removeImage() {
        this.state.receiptImage = null;
        this.state.receiptImagePreview = null;
    }

    async confirm() {
        await this.props.onConfirm({
            payWithCash: this.state.payWithCash,
            billReference: this.state.billReference,
            receiptImage: this.state.receiptImage,
        });
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
