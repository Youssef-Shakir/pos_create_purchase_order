# POS Create Purchase Order

Create Purchase Orders directly from the Point of Sale screen in Odoo 18.

## Features

- **Create PO from POS**: One-click purchase order creation from POS screen
- **Configurable PO State**: Set default PO state (Draft, RFQ Sent, To Approve, Purchase Order, Locked)
- **Default Vendor**: Configure a default vendor for POS purchase orders
- **Pay with POS Cash**: Option to pay vendor directly from POS cash drawer
- **Receipt Image Capture**: Take photo or upload vendor receipt/invoice image
- **Bill Reference**: Enter vendor bill/invoice reference number
- **Quick Process Wizard**: Complete PO workflow in one screen (Review → Receive → Bill → Payment)
- **POS Integration**: View purchase orders created from each POS config
- **Filter & Group**: Filter and group purchase orders by POS origin

## Installation

1. Copy the `pos_create_purchase_order` folder to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the module from Apps menu

## Configuration

1. Go to **Point of Sale > Configuration > Settings**
2. Enable **Create Purchase Orders**
3. Select default **PO State** (Draft, RFQ Sent, To Approve, Purchase Order, Locked)
4. Optionally set a **Default Vendor** for POS purchase orders

## Usage

### Creating a Purchase Order

1. Open POS session
2. Add products to the order
3. Select a customer/vendor (or use default vendor from settings)
4. Click **Create PO** button in control buttons
5. In the popup:
   - Toggle **Pay with POS Cash** if paying from cash drawer
   - Enter **Bill/Invoice Reference** (optional)
   - Capture or upload **Receipt Image** (optional)
6. Click **Create Purchase Order**

### Pay with POS Cash

When enabled, the module will:
- Create a cash out entry in the POS session
- Record the payment with vendor partner for easy reconciliation
- Journal entry: Credit Cash, Debit Accounts Payable (with partner)

### Viewing POS Purchase Orders

- Go to **Purchase > Orders > Purchase Orders**
- Use filter **From POS** to see all POS-created orders
- Group by **POS Config** or **POS Origin**

### Quick Process Wizard

The Quick Process wizard simplifies the entire PO workflow in a single screen:

1. **Review PO**: View order details and confirm the purchase order
2. **Receive Inventory**: Validate receipts and receive all items
3. **Create Bill**: Generate vendor bill with auto-filled reference
4. **Register Payment**: Record payment and reconcile with the bill

To use:
1. Open any Purchase Order
2. Click **Quick Process** button in the top-right button box
3. Follow the step-by-step wizard

## Technical Details

### Models Extended

- `purchase.order`: Added POS-related fields
- `pos.config`: Added PO creation settings
- `pos.session`: Extended for data loading

### New Fields on Purchase Order

| Field | Type | Description |
|-------|------|-------------|
| `pos_origin` | Boolean | Indicates order was created from POS |
| `pos_config_id` | Many2one | Link to POS Config |
| `pos_bill_reference` | Char | Vendor bill/invoice reference |
| `pos_receipt_image` | Binary | Uploaded receipt image |
| `pos_paid_with_cash` | Boolean | Paid from POS cash drawer |

### New Models

| Model | Type | Description |
|-------|------|-------------|
| `po.quick.process` | Transient | Wizard for quick PO processing |

### Dependencies

- `point_of_sale`
- `purchase`
- `purchase_stock`
- `account`

## Translations

- English (default)
- Arabic (العربية)

## Authors

**Developed by:**
- [Donialink](https://www.donialink.com)
- Yousif Shakir

## License

LGPL-3

## Support

For issues and feature requests, please contact the developers.
