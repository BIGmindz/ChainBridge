//! PAC-STRAT-P49: Speed Moat Verification
//! =======================================
//! 
//! CONSTITUTIONAL LIMIT: 12ms per transaction
//! 
//! This benchmark hammers the Critical Path:
//! INPUT → Hardware Check → JSON Parse → Schema Check → Logic Check → DECISION
//! 
//! We measure the hot-path to prove we are faster than bureaucracy.

use criterion::{criterion_group, criterion_main, Criterion, BenchmarkId, Throughput};
use std::hint::black_box;
use chainbridge_kernel::erp_shield::{NetSuiteInvoice, InvoiceLineItem};

/// Build a valid invoice for benchmarking
fn build_valid_invoice() -> NetSuiteInvoice {
    NetSuiteInvoice {
        internal_id: "INV-2026-001".to_string(),
        entity_id: "CUST-001".to_string(),
        subsidiary: "1".to_string(),
        currency: "USD".to_string(),
        total_amount: 15000, // $150.00 in cents
        line_items: vec![
            InvoiceLineItem {
                item_id: "ITEM-001".to_string(),
                quantity: 10,
                unit_price: 1000, // $10.00 in cents
                line_total: 10000, // $100.00 in cents
            },
            InvoiceLineItem {
                item_id: "ITEM-002".to_string(),
                quantity: 5,
                unit_price: 1000, // $10.00 in cents
                line_total: 5000, // $50.00 in cents
            },
        ],
        memo: None,
    }
}

/// Build an invoice with invalid currency
fn build_invalid_currency_invoice() -> NetSuiteInvoice {
    NetSuiteInvoice {
        internal_id: "INV-2026-002".to_string(),
        entity_id: "CUST-001".to_string(),
        subsidiary: "1".to_string(),
        currency: "FAKE".to_string(), // Invalid!
        total_amount: 10000,
        line_items: vec![
            InvoiceLineItem {
                item_id: "ITEM-001".to_string(),
                quantity: 10,
                unit_price: 1000,
                line_total: 10000,
            },
        ],
        memo: None,
    }
}

/// Build an invoice with math mismatch (logic error)
fn build_math_mismatch_invoice() -> NetSuiteInvoice {
    NetSuiteInvoice {
        internal_id: "INV-2026-003".to_string(),
        entity_id: "CUST-001".to_string(),
        subsidiary: "1".to_string(),
        currency: "USD".to_string(),
        total_amount: 99999, // Wrong total!
        line_items: vec![
            InvoiceLineItem {
                item_id: "ITEM-001".to_string(),
                quantity: 10,
                unit_price: 1000,
                line_total: 10000,
            },
        ],
        memo: None,
    }
}

/// Benchmark: Pure validation logic (no network, no JSON parsing)
fn bench_validation_logic(c: &mut Criterion) {
    let valid = build_valid_invoice();
    let invalid_currency = build_invalid_currency_invoice();
    let math_mismatch = build_math_mismatch_invoice();
    
    let mut group = c.benchmark_group("validation_logic");
    
    // Valid invoice - should pass all gates
    group.bench_function("valid_invoice", |b| {
        b.iter(|| {
            black_box(valid.validate())
        })
    });
    
    // Invalid currency - should fail at currency gate
    group.bench_function("invalid_currency", |b| {
        b.iter(|| {
            black_box(invalid_currency.validate())
        })
    });
    
    // Math mismatch - should fail at total gate
    group.bench_function("math_mismatch", |b| {
        b.iter(|| {
            black_box(math_mismatch.validate())
        })
    });
    
    group.finish();
}

/// Benchmark: JSON parsing + validation (full pipeline minus network)
fn bench_full_pipeline(c: &mut Criterion) {
    // Simulate raw JSON input (using the serde rename fields)
    let valid_json = r#"{
        "internalId": "INV-2026-001",
        "entityId": "CUST-001",
        "subsidiary": "1",
        "currency": "USD",
        "totalAmount": 15000,
        "lineItems": [
            {"itemId": "ITEM-001", "quantity": 10, "unitPrice": 1000, "lineTotal": 10000},
            {"itemId": "ITEM-002", "quantity": 5, "unitPrice": 1000, "lineTotal": 5000}
        ]
    }"#;
    
    let malformed_json = r#"{ "internalId": "INV-001", "entityId": "#; // Truncated
    
    let mut group = c.benchmark_group("full_pipeline");
    
    // Valid JSON -> Parse -> Validate
    group.bench_function("json_parse_and_validate", |b| {
        b.iter(|| {
            let invoice: Result<NetSuiteInvoice, _> = serde_json::from_str(black_box(valid_json));
            match invoice {
                Ok(inv) => black_box(inv.validate()),
                Err(_) => Err(chainbridge_kernel::erp_shield::ValidationError::EmptyField("parse")),
            }
        })
    });
    
    // Malformed JSON -> Parse (should fail fast)
    group.bench_function("malformed_json_rejection", |b| {
        b.iter(|| {
            let result: Result<NetSuiteInvoice, _> = serde_json::from_str(black_box(malformed_json));
            black_box(result.is_err())
        })
    });
    
    group.finish();
}

/// Benchmark: Throughput test - 1000 mixed requests
fn bench_throughput(c: &mut Criterion) {
    let valid = build_valid_invoice();
    let invalid = build_invalid_currency_invoice();
    let mismatch = build_math_mismatch_invoice();
    
    let mut group = c.benchmark_group("throughput");
    group.throughput(Throughput::Elements(1000));
    
    group.bench_function("1000_mixed_validations", |b| {
        b.iter(|| {
            for i in 0..1000 {
                match i % 3 {
                    0 => { black_box(valid.validate()); },
                    1 => { black_box(invalid.validate()); },
                    _ => { black_box(mismatch.validate()); },
                }
            }
        })
    });
    
    group.finish();
}

/// Benchmark: Scaling with line items
fn bench_scaling(c: &mut Criterion) {
    let mut group = c.benchmark_group("scaling");
    
    for size in [1, 10, 50, 100].iter() {
        let mut invoice = NetSuiteInvoice {
            internal_id: "INV-SCALE".to_string(),
            entity_id: "CUST-001".to_string(),
            subsidiary: "1".to_string(),
            currency: "USD".to_string(),
            total_amount: 0,
            line_items: Vec::with_capacity(*size),
            memo: None,
        };
        
        for i in 0..*size {
            invoice.line_items.push(InvoiceLineItem {
                item_id: format!("ITEM-{:03}", i),
                quantity: 1,
                unit_price: 100,
                line_total: 100,
            });
        }
        invoice.total_amount = (*size as i64) * 100;
        
        group.bench_with_input(BenchmarkId::new("line_items", size), &invoice, |b, inv| {
            b.iter(|| black_box(inv.validate()))
        });
    }
    
    group.finish();
}

criterion_group!(
    benches,
    bench_validation_logic,
    bench_full_pipeline,
    bench_throughput,
    bench_scaling
);
criterion_main!(benches);
