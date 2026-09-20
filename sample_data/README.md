# 📁 Sample Datasets for Testing & Demo

This folder contains sample multi-file datasets ready to drag-and-drop into the **Data Q&A** application.

---

## 📊 Datasets Overview

### 1. `customers.csv`
Contains customer profiles, industry sectors, region, and signup dates.
- **Key Columns:** `customer_id`, `customer_name`, `email`, `region`, `industry`, `signup_date`
- **Primary Key:** `customer_id`

### 2. `orders.csv`
Contains transaction records, order quantities, status, order dates, and total amounts.
- **Key Columns:** `order_id`, `customer_id`, `product_id`, `order_date`, `quantity`, `unit_price`, `total_amount`, `status`
- **Foreign Keys:** `customer_id` → `customers.csv`, `product_id` → `products.xlsx`

### 3. `products.xlsx` (Multi-sheet Excel workbook)
- **Sheet 1: `Products`**: Product catalog with categories, unit prices, and launch dates.
  - Columns: `product_id`, `product_name`, `category`, `subcategory`, `unit_price`, `launch_date`
- **Sheet 2: `Pricing Tiers`**: Tiered discount structures based on volume.
  - Columns: `tier`, `discount_pct`, `min_quantity`, `notes`
- **Sheet 3: `Notes`**: Informational sheet (automatically recognized as non-tabular notes and handled safely).

---

## 💡 Example Questions to Try

### Single-File Questions
1. *"What is the total revenue from orders?"*
2. *"Show the monthly trend of order volume."*
3. *"Which industry has the most customers?"*

### Cross-File Analytical Questions (Multi-Table Joins)
1. *"What is the total revenue by product category?"* (Joins `orders.csv` + `products.xlsx`)
2. *"Who are the top 5 customers by spend and which industry are they in?"* (Joins `customers.csv` + `orders.csv`)
3. *"Show revenue breakdown by customer region and product category."* (Joins `customers.csv` + `orders.csv` + `products.xlsx`)

### Conversational Follow-Ups
- *Initial:* *"What are the top selling products?"*
- *Follow-up:* *"Filter that down to only the Software category."*
- *Follow-up:* *"Show this as a bar chart."*
