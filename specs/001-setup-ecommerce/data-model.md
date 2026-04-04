# Data Model: Products and Orders

## Entities

### Product (DTO)
Represents a sellable item.
- `id`: str (Primary Key, prefixed ULID — e.g. `prd_01jq3v...`)
- `name`: str (Required, max_length=255)
- `price`: Decimal (Required, positive)
- `stock`: int (Required, non-negative)

### Order (DTO)
Represents a customer purchase.
- `id`: str (Primary Key, prefixed ULID — e.g. `ord_01jq3v...`)
- `date`: datetime (Auto-now-add)
- `total`: Decimal (Calculated sum of OrderItems)
- `items`: List[OrderItem] (Related items)

### OrderItem (DTO)
Links a product to an order with fixed price at purchase time.
- `id`: str (Primary Key, prefixed ULID — e.g. `itm_01jq3v...`)
- `product_id`: str (Foreign Key to Product)
- `order_id`: str (Foreign Key to Order)
- `quantity`: int (Required, positive)
- `price_at_purchase`: Decimal (Required, positive)

## ID Format

All IDs use the Stripe-style prefixed ULID pattern: `<prefix>_<lowercase_ulid>`.

| Entity    | Prefix | Example                              |
|-----------|--------|--------------------------------------|
| Product   | `prd`  | `prd_01jq3v7k8m0000000000000000`     |
| Order     | `ord`  | `ord_01jq3v7k8m0000000000000000`     |
| OrderItem | `itm`  | `itm_01jq3v7k8m0000000000000000`     |

IDs are generated at model creation time via `project.ids` and stored as `CharField(max_length=64)` primary keys.

## Relationships

- **Order 1:N OrderItems**: An order consists of one or more items.
- **Product 1:N OrderItems**: A product can be part of many order items (orders).

## Validation Rules

- **Product price** MUST be greater than zero.
- **Product stock** MUST NOT be negative.
- **Order total** MUST equal the sum of its items' (quantity * price_at_purchase).
- **OrderItem quantity** MUST be at least 1.

## State Transitions

- **Order**: Created -> Paid (out of scope for MVP)
