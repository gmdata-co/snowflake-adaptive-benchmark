# TPC-H Query Performance Test Categories

Categorizes all 22 TPC-H benchmark queries (TPCH_SF100 dataset, ~100GB) by performance test type.

---

## 1. Simple Aggregation & Filtering
**Tests:** Table scan speed, aggregation performance, predicate pushdown

- **Q1** - Multiple aggregations (SUM, AVG, COUNT) with GROUP BY on 600M row table
- **Q6** - Single aggregation with selective filtering (date range, BETWEEN)

---

## 2. Basic Joins (2-4 tables)
**Tests:** Join algorithms, join order optimization

- **Q3** - 3-way join with aggregation and date filtering
- **Q10** - 4-way join with selective filter and high-cardinality GROUP BY
- **Q12** - 2-way join with CASE aggregations and multiple date predicates
- **Q14** - 2-way join with conditional aggregation and pattern matching (LIKE)
- **Q19** - 2-way join with complex OR conditions across multiple predicates

---

## 3. Complex Joins (5+ tables)
**Tests:** Many-way join optimization, star schema performance

- **Q5** - 6-way join with revenue calculation and geographic filtering
- **Q7** - 6-way join with self-join on NATION, complex OR, date extraction
- **Q8** - 8-way join with market share calculation and self-join
- **Q9** - 6-way join with profit calculations and pattern matching

---

## 4. Subqueries & Semi-Joins
**Tests:** Subquery materialization, IN/NOT IN optimization, semi-join strategies

- **Q2** - Correlated subquery with MIN aggregation in 5-way join
- **Q4** - EXISTS clause with correlated condition
- **Q11** - Subquery in HAVING clause with threshold comparison
- **Q16** - NOT IN subquery with DISTINCT COUNT aggregation
- **Q18** - IN subquery with aggregation filter (HAVING)

---

## 5. Correlated & Nested Subqueries
**Tests:** Decorrelation optimization, deep nesting, multiple subquery levels

- **Q17** - Correlated subquery comparing to calculated average
- **Q20** - 3-level nested IN subqueries with innermost correlation
- **Q22** - Derived table with nested subquery and NOT EXISTS

---

## 6. Advanced Patterns
**Tests:** CTE optimization, outer joins, complex EXISTS patterns

- **Q13** - LEFT OUTER JOIN with double aggregation and NULL handling
- **Q15** - CTE (WITH clause) referenced multiple times with MAX subquery
- **Q21** - Both EXISTS and NOT EXISTS with self-joins (l1, l2, l3) on 4-way join

---

## Quick Reference

| Complexity | Queries |
|------------|---------|
| **Low** (Warm-up) | Q1, Q6 |
| **Medium** (Standard OLAP) | Q3, Q4, Q10, Q12, Q14, Q16, Q18, Q19 |
| **High** (Stress Test) | Q2, Q5, Q7, Q8, Q9, Q11, Q13, Q15, Q17, Q20, Q21, Q22 |

**Dataset:** SNOWFLAKE_SAMPLE_DATA.TPCH_SF100 (~100GB)
- LINEITEM: 600M rows | ORDERS: 150M rows | PARTSUPP: 80M rows | PART: 20M rows
- CUSTOMER: 15M rows | SUPPLIER: 1M rows | NATION: 25 rows | REGION: 5 rows
