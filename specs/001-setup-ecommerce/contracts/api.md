# API Contract: Products and Orders

## Endpoints

### Products API

- **GET /products/**: List all products.
  - Returns: `List[ProductDTO]`
- **GET /products/{id}/**: Get a single product by ID.
  - Returns: `ProductDTO`
- **POST /products/**: Create a new product.
  - Input: `{name: str, price: Decimal, stock: int}`
  - Returns: `ProductDTO`

### Orders API

- **GET /orders/**: List all orders.
  - Returns: `List[OrderDTO]`
- **GET /orders/{id}/**: Get a single order by ID.
  - Returns: `OrderDTO`
- **POST /orders/**: Create a new order.
  - Input: `{items: [{product_id: str, quantity: int}]}`
  - Returns: `OrderDTO`

## Response Formats

- All responses are in JSON format.
- Dates are ISO 8601 strings.
- IDs are Stripe-style prefixed ULID strings (e.g. `prd_01jq3v...`, `ord_01jq3v...`).
- Currency fields are decimal strings.
