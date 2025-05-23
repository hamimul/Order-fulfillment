# API Testing Guide

This guide provides comprehensive examples for testing the Order Fulfillment System API.

## Table of Contents

1. [Setup](#setup)
2. [Authentication](#authentication)
3. [Products API](#products-api)
4. [Inventory API](#inventory-api)
5. [Orders API](#orders-api)
6. [Health Check API](#health-check-api)
7. [Testing Tools](#testing-tools)
8. [Performance Testing](#performance-testing)

## Setup

Base URL for all API endpoints:
- Development: `http://localhost:8000/api/v1/`
- Production: `https://yourdomain.com/api/v1/`

## Authentication

Currently, the API allows anonymous access for demonstration purposes. In production, implement proper authentication:

```bash
# Example with API key (when implemented)
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/v1/orders/
```

## Products API

### List Products

```bash
# Get all products
curl -X GET http://localhost:8000/api/v1/products/

# Get products with pagination
curl -X GET "http://localhost:8000/api/v1/products/?page=2&page_size=10"

# Search products
curl -X GET "http://localhost:8000/api/v1/products/?search=smartphone"

# Filter active products
curl -X GET "http://localhost:8000/api/v1/products/?is_active=true"
```

### Get Product Details

```bash
curl -X GET http://localhost:8000/api/v1/products/1/
```

### Create Product

```bash
curl -X POST http://localhost:8000/api/v1/products/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Product",
    "sku": "NEW-001",
    "price": "99.99",
    "description": "A new product for testing",
    "initial_stock": 100
  }'
```

### Update Product

```bash
curl -X PATCH http://localhost:8000/api/v1/products/1/ \
  -H "Content-Type: application/json" \
  -d '{
    "price": "89.99",
    "description": "Updated description"
  }'
```

### Get Low Stock Products

```bash
curl -X GET http://localhost:8000/api/v1/products/low_stock/
```

### Get Product Stock History

```bash
curl -X GET http://localhost:8000/api/v1/products/1/stock_history/
```

## Inventory API

### List Inventory Items

```bash
# Get all inventory items
curl -X GET http://localhost:8000/api/v1/inventory/

# Filter low stock items
curl -X GET "http://localhost:8000/api/v1/inventory/?low_stock=true"

# Filter out of stock items
curl -X GET "http://localhost:8000/api/v1/inventory/?out_of_stock=true"
```

### Get Inventory Item Details

```bash
curl -X GET http://localhost:8000/api/v1/inventory/1/
```

### Adjust Inventory

```bash
# Add stock
curl -X POST http://localhost:8000/api/v1/inventory/1/adjust/ \
  -H "Content-Type: application/json" \
  -d '{
    "adjustment_type": "add",
    "quantity": 50,
    "notes": "Received new shipment",
    "reference_number": "PO-2024-001"
  }'

# Remove stock
curl -X POST http://localhost:8000/api/v1/inventory/1/adjust/ \
  -H "Content-Type: application/json" \
  -d '{
    "adjustment_type": "remove",
    "quantity": 10,
    "notes": "Damaged goods",
    "reference_number": "DMG-001"
  }'

# Set specific quantity
curl -X POST http://localhost:8000/api/v1/inventory/1/adjust/ \
  -H "Content-Type: application/json" \
  -d '{
    "adjustment_type": "set",
    "quantity": 100,
    "notes": "Physical inventory count",
    "reference_number": "INV-COUNT-2024"
  }'
```

### Get Inventory Transactions

```bash
curl -X GET http://localhost:8000/api/v1/inventory/1/transactions/
```

### Get Inventory History

```bash
curl -X GET http://localhost:8000/api/v1/inventory/1/history/
```

### Get Inventory Summary

```bash
curl -X GET http://localhost:8000/api/v1/inventory/summary/
```

## Orders API

### List Orders

```bash
# Get all orders
curl -X GET http://localhost:8000/api/v1/orders/

# Filter by status
curl -X GET "http://localhost:8000/api/v1/orders/?status=pending"

# Filter by priority
curl -X GET "http://localhost:8000/api/v1/orders/?priority=high"

# Filter by customer email
curl -X GET "http://localhost:8000/api/v1/orders/?customer_email=customer@example.com"

# Get stale orders only
curl -X GET "http://localhost:8000/api/v1/orders/?stale_only=true"

# Filter by date range
curl -X GET "http://localhost:8000/api/v1/orders/?date_from=2024-01-01&date_to=2024-01-31"
```

### Create Single Order

```bash
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "priority": "normal",
    "shipping_address": "123 Main St, City, State 12345",
    "billing_address": "123 Main St, City, State 12345",
    "payment_method": "credit_card",
    "items": [
      {
        "product_id": 1,
        "quantity": 2
      },
      {
        "product_id": 3,
        "quantity": 1
      }
    ]
  }'
```

### Create Bulk Orders

```bash
curl -X POST http://localhost:8000/api/v1/orders/bulk_create/ \
  -H "Content-Type: application/json" \
  -d '{
    "orders": [
      {
        "customer_name": "Customer 1",
        "customer_email": "customer1@example.com",
        "items": [
          {"product_id": 1, "quantity": 1}
        ]
      },
      {
        "customer_name": "Customer 2",
        "customer_email": "customer2@example.com",
        "items": [
          {"product_id": 2, "quantity": 2}
        ]
      },
      {
        "customer_name": "Customer 3",
        "customer_email": "customer3@example.com",
        "items": [
          {"product_id": 1, "quantity": 1},
          {"product_id": 3, "quantity": 1}
        ]
      }
    ]
  }'
```

### Get Order Details

```bash
curl -X GET http://localhost:8000/api/v1/orders/ORDER_ID_HERE/
```

### Cancel Order

```bash
curl -X POST http://localhost:8000/api/v1/orders/ORDER_ID_HERE/cancel/
```

### Get Order History

```bash
curl -X GET http://localhost:8000/api/v1/orders/ORDER_ID_HERE/history/
```

### Get Order Tracking

```bash
curl -X GET http://localhost:8000/api/v1/orders/ORDER_ID_HERE/tracking/
```

### Search Orders by Customer

```bash
curl -X GET "http://localhost:8000/api/v1/orders/search_by_customer/?q=john@example.com"
```

### Get Order Statistics

```bash
curl -X GET http://localhost:8000/api/v1/orders/statistics/
```

### Trigger Stale Order Check

```bash
curl -X POST http://localhost:8000/api/v1/orders/check_stale/
```

## Health Check API

### Basic Health Check

```bash
curl -X GET http://localhost:8000/health/
```

### System Metrics

```bash
curl -X GET http://localhost:8000/health/metrics/
```

## Testing Tools

### Using HTTPie (More User-Friendly)

Install HTTPie: `pip install httpie`

```bash
# List products
http GET localhost:8000/api/v1/products/

# Create order
http POST localhost:8000/api/v1/orders/ \
  customer_name="Jane Doe" \
  customer_email="jane@example.com" \
  items:='[{"product_id": 1, "quantity": 2}]'

# Get order details
http GET localhost:8000/api/v1/orders/ORDER_ID_HERE/
```

### Using Postman

1. Import the OpenAPI specification from `http://localhost:8000/swagger.json`
2. Create a new environment with base URL: `http://localhost:8000/api/v1`
3. Use the pre-generated requests from the specification

### Using Python Requests

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Create order
order_data = {
    "customer_name": "Python Test",
    "customer_email": "python@test.com",
    "items": [
        {"product_id": 1, "quantity": 2}
    ]
}

response = requests.post(f"{BASE_URL}/orders/", json=order_data)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Get order details
if response.status_code == 201:
    order_id = response.json()["order_id"]
    order_response = requests.get(f"{BASE_URL}/orders/{order_id}/")
    print(f"Order: {order_response.json()}")
```

## Performance Testing

### Load Testing with Apache Bench

```bash
# Test product listing endpoint
ab -n 1000 -c 10 http://localhost:8000/api/v1/products/

# Test order creation (requires JSON payload)
ab -n 100 -c 5 -p order_payload.json -T application/json http://localhost:8000/api/v1/orders/
```

### Load Testing with Hey

Install: `go install github.com/rakyll/hey@latest`

```bash
# Test product listing
hey -n 1000 -c 10 http://localhost:8000/api/v1/products/

# Test with POST data
hey -n 100 -c 5 -m POST -H "Content-Type: application/json" \
  -d '{"customer_name":"Load Test","customer_email":"test@example.com","items":[{"product_id":1,"quantity":1}]}' \
  http://localhost:8000/api/v1/orders/
```

### Using Built-in Load Testing

```bash
# Use the management command for comprehensive load testing
python manage.py load_test --orders 100 --threads 10

# Custom load test
python manage.py load_test --orders 500 --threads 20 --delay 0.1
```

## Error Handling Examples

### Handling Validation Errors

```bash
# Try to create order with invalid data
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "",
    "customer_email": "invalid-email",
    "items": []
  }'

# Expected response: 400 Bad Request with validation errors
```

### Handling Insufficient Stock

```bash
# Try to order more than available stock
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer",
    "customer_email": "test@example.com",
    "items": [
      {
        "product_id": 1,
        "quantity": 99999
      }
    ]
  }'

# Expected response: 400 Bad Request with stock error
```

### Handling Not Found Errors

```bash
# Try to get non-existent order
curl -X GET http://localhost:8000/api/v1/orders/non-existent-id/

# Expected response: 404 Not Found
```

## API Response Examples

### Successful Order Creation

```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "status": "pending",
  "total_amount": "199.98",
  "priority": "normal",
  "items": [
    {
      "product_id": 1,
      "product_name": "Smartphone X Pro",
      "product_sku": "SMT-001",
      "quantity": 2,
      "price": "99.99",
      "total_price": "199.98"
    }
  ],
  "created_at": "2024-01-20T10:30:00Z",
  "version": 1
}
```

### Error Response

```json
{
  "detail": "Insufficient stock for Smartphone X Pro. Available: 5, Requested: 10"
}
```

### Validation Error Response

```json
{
  "customer_email": ["Enter a valid email address."],
  "items": ["This field is required."]
}
```

## Testing Checklist

- [ ] Create products with inventory
- [ ] Test product listing and filtering
- [ ] Create single orders with valid data
- [ ] Create bulk orders
- [ ] Test order status progression
- [ ] Test inventory adjustments
- [ ] Test insufficient stock scenarios
- [ ] Test order cancellation
- [ ] Test search functionality
- [ ] Test health check endpoints
- [ ] Test error handling
- [ ] Test rate limiting (if enabled)
- [ ] Test concurrent order creation
- [ ] Verify stale order detection
- [ ] Test backup and restore functionality

This guide covers the essential API testing scenarios for the Order Fulfillment System. Use these examples as a starting point for your testing and adapt them to your specific requirements.